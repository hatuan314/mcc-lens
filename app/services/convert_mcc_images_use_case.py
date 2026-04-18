"""
Convert MCC Images Use Case.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from app.models.mcc_entry import MCCEntry
from app.services.florence2_vision_service import Florence2VisionService
from app.services.table_reconstruction_service import TableReconstructionService
from app.services.mcc_parser_service import MCCParserService
from app.repositories.mcc_image_repository import MCCImageRepository
from app.repositories.mcc_json_repository import MCCJsonRepository


class ConvertMCCImagesUseCase:
    """
    Use case for orchestrating the conversion of MCC images to JSON.

    Pipeline: Vision (OCR with regions) → Table Reconstruction → Parser → JSON Output
    """

    def __init__(
        self,
        vision_service: Optional[Florence2VisionService] = None,
        table_reconstructor: Optional[TableReconstructionService] = None,
        parser_service: Optional[MCCParserService] = None,
        image_repository: Optional[MCCImageRepository] = None,
        json_repository: Optional[MCCJsonRepository] = None,
    ):
        self.vision_service = vision_service or Florence2VisionService()
        self.table_reconstructor = table_reconstructor or TableReconstructionService()
        self.parser_service = parser_service or MCCParserService()
        self.image_repository = image_repository or MCCImageRepository()
        self.json_repository = json_repository or MCCJsonRepository()

    def execute(
        self,
        input_dir: Path,
        output_path: Path,
        device: Optional[str] = None,
        y_threshold_pct: float = 0.01,
        resume: bool = False,
    ) -> Dict[str, any]:
        """
        Execute the conversion pipeline.

        Args:
            input_dir: Directory containing input images.
            output_path: Path to output JSON file.
            device: Device to run inference on (cuda/mps/cpu).
            y_threshold_pct: Y-axis threshold for row grouping (default 0.01).
            resume: If True, skip images already processed (not implemented yet).

        Returns:
            Dictionary with execution results.
        """
        if device:
            self.vision_service = Florence2VisionService(device=device)

        # Update y_threshold if provided
        if y_threshold_pct != 0.01:
            self.table_reconstructor = TableReconstructionService(y_threshold_pct)

        logger.info(f"Starting conversion from {input_dir} to {output_path}")
        logger.info(f"Using device: {self.vision_service.device}")
        logger.info(f"Y threshold for row grouping: {y_threshold_pct}")

        images = self.image_repository.list_images(input_dir)
        logger.info(f"Found {len(images)} images to process")

        all_entries: List[MCCEntry] = []
        errors: List[Dict[str, str]] = []
        processed = 0

        for image_path in images:
            try:
                logger.info(f"Processing: {image_path.name}")

                # Step 1: Extract regions with bounding boxes
                regions = self.vision_service.extract_regions(image_path)
                logger.debug(f"Extracted {len(regions)} regions from {image_path.name}")

                # Step 2: Reconstruct table from regions
                from PIL import Image
                image = Image.open(image_path)
                image_size = (image.width, image.height)
                rows = self.table_reconstructor.reconstruct(regions, image_size)
                logger.debug(f"Reconstructed {len(rows)} table rows")

                # Step 3: Parse rows into MCC entries
                entries = self.parser_service.parse(rows, image_path.name)
                all_entries.extend(entries)
                processed += 1

                logger.info(f"Parsed {len(entries)} entries from {image_path.name}")

            except Exception as e:
                logger.warning(f"Failed to process {image_path.name}: {e}")
                errors.append({
                    "file": image_path.name,
                    "error": str(e),
                })

        # Step 4: Deduplicate entries by MCC code
        unique_entries = self._deduplicate_entries(all_entries)
        logger.info(
            f"Total entries: {len(unique_entries)} "
            f"(parsed={sum(1 for e in unique_entries if not e.unparsed)}, "
            f"unparsed={sum(1 for e in unique_entries if e.unparsed)})"
        )

        # Step 5: Save to JSON
        self.json_repository.save(unique_entries, output_path)
        logger.info(f"Saved {len(unique_entries)} entries to {output_path}")

        return {
            "total_images": len(images),
            "processed": processed,
            "total_entries": len(unique_entries),
            "errors": errors,
            "output_path": str(output_path),
        }

    def _deduplicate_entries(self, entries: List[MCCEntry]) -> List[MCCEntry]:
        """
        Deduplicate entries by MCC code.

        For duplicate MCC codes:
        - Merge title_description and included with newline separator
        - Union similar_merchants lists
        - Keep all entries with unparsed=True intact

        Args:
            entries: List of MCCEntry objects.

        Returns:
            Deduplicated list of MCCEntry objects.
        """
        seen: Dict[str, MCCEntry] = {}
        unparsed_entries: List[MCCEntry] = []

        for entry in entries:
            if entry.unparsed:
                unparsed_entries.append(entry)
                continue

            existing = seen.get(entry.mcc)
            if existing is None:
                seen[entry.mcc] = entry
            else:
                # Merge title_description and included
                if entry.title_description and entry.title_description not in existing.title_description:
                    if existing.title_description:
                        existing.title_description += "\n" + entry.title_description
                    else:
                        existing.title_description = entry.title_description

                if entry.included and entry.included not in existing.included:
                    if existing.included:
                        existing.included += "\n" + entry.included
                    else:
                        existing.included = entry.included

                # Union similar_merchants
                existing_merchants = set(existing.similar_merchants)
                new_merchants = set(entry.similar_merchants)
                existing.similar_merchants = list(existing_merchants.union(new_merchants))

        return list(seen.values()) + unparsed_entries
