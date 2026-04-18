"""
Convert MCC Images Use Case.
"""

import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.mcc_entry import MCCEntry
from app.services.protocols import (
    CheckpointRepository,
    ImageRepository,
    JsonRepository,
    OCRService,
    TableParser,
)
from app.views.progress_bar_view import ProgressBarView


def _nfc(value: str) -> str:
    """Normalize filename to NFC for stable cross-platform comparison."""
    return unicodedata.normalize("NFC", value)


class ConvertMCCImagesUseCase:
    """
    Use case for orchestrating the conversion of MCC images to JSON.

    Pipeline: OCR (Surya) → TableParser → Dedup → Sort → JSON Output
    """

    def __init__(
        self,
        ocr_service: OCRService,
        table_parser: TableParser,
        image_repository: ImageRepository,
        json_repository: JsonRepository,
        checkpoint_repository: CheckpointRepository,
        progress_bar: Optional[ProgressBarView] = None,
    ):
        self.ocr_service = ocr_service
        self.table_parser = table_parser
        self.image_repository = image_repository
        self.json_repository = json_repository
        self.checkpoint_repository = checkpoint_repository
        self.progress_bar = progress_bar

    def execute(
        self,
        input_dir: Path,
        output_path: Path,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the conversion pipeline.

        Args:
            input_dir: Directory containing input images.
            output_path: Path to output JSON file.
            resume: If True, skip images already processed.

        Returns:
            Dictionary with execution results.
        """
        logger.info(f"Starting conversion from {input_dir} to {output_path}")

        images = self.image_repository.list_images(input_dir)
        logger.info(f"Found {len(images)} images to process")

        # Load checkpoint for resume
        processed_files: set[str] = set()
        if resume:
            processed_files = set(self.checkpoint_repository.load())
            if processed_files:
                logger.info(
                    f"Resuming: {len(processed_files)} images already processed"
                )

        all_entries: List[MCCEntry] = []
        errors: List[Dict[str, str]] = []
        processed = 0

        with ProgressBarView(total=len(images), desc="Converting", unit="img") as bar:
            for image_path in images:
                nfc_name = _nfc(image_path.name)
                if nfc_name in processed_files:
                    bar.update()
                    continue

                try:
                    logger.info(f"Processing: {image_path.name}")

                    image = self.image_repository.read(image_path)
                    image_width = image.width

                    # Step 1: Extract OCR lines
                    lines = self.ocr_service.extract_lines(image)
                    logger.debug(f"Extracted {len(lines)} lines from {image_path.name}")

                    # Step 2: Parse table
                    entries = self.table_parser.parse(
                        lines, image_width, source_image=nfc_name
                    )
                    all_entries.extend(entries)
                    processed += 1

                    # Mark checkpoint after successful processing
                    if resume:
                        self.checkpoint_repository.mark_done(nfc_name)
                        processed_files.add(nfc_name)

                    logger.info(f"Parsed {len(entries)} entries from {image_path.name}")

                except Exception as e:
                    logger.warning(f"Failed to process {image_path.name}: {e}")
                    errors.append({
                        "file": image_path.name,
                        "error": str(e),
                    })

                bar.update()

        # Step 3: Deduplicate entries by MCC code (keep longer description)
        unique_entries = self._deduplicate_entries(all_entries)

        # Step 4: Sort by MCC code
        unique_entries.sort(key=lambda e: e.mcc.zfill(4) if e.mcc.isdigit() else e.mcc)

        logger.info(
            f"Total entries: {len(unique_entries)} "
            f"(parsed={sum(1 for e in unique_entries if not e.unparsed)}, "
            f"unparsed={sum(1 for e in unique_entries if e.unparsed)})"
        )

        # Step 5: Save to JSON
        self.json_repository.save(unique_entries, output_path)
        logger.info(f"Saved {len(unique_entries)} entries to {output_path}")

        # Clear checkpoint on full success
        if resume:
            self.checkpoint_repository.clear()

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

        For duplicate MCC codes, keep the entry with the longer description.

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
                # Keep entry with longer description
                existing_desc = existing.description or ""
                new_desc = entry.description or ""
                if len(new_desc) > len(existing_desc):
                    seen[entry.mcc] = entry

        return list(seen.values()) + unparsed_entries
