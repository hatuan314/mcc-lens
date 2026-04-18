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

    Pipeline: Batch OCR (Surya) → TableParser → Dedup → Sort → JSON Output

    Batch processing: BATCH_SIZE=8 hardcoded, mini-batch strategy to optimize throughput.
    """

    BATCH_SIZE = 8

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
        Execute the conversion pipeline with batch processing.

        Pipeline: Group images → Batch OCR → Per-image Parse → Checkpoint → Dedup → Sort → Save

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

        # Group images into batches
        batches = self._group_into_batches(images)
        logger.info(
            f"Processing {len(images)} images in {len(batches)} batches of {self.BATCH_SIZE}"
        )

        with ProgressBarView(total=len(images), desc="Converting", unit="img") as bar:
            for batch_idx, batch_paths in enumerate(batches):
                batch_num = batch_idx + 1
                logger.debug(
                    f"Batch {batch_num}/{len(batches)}: {len(batch_paths)} images"
                )

                # Check if entire batch is already processed
                nfc_batch_names = [_nfc(p.name) for p in batch_paths]
                if all(name in processed_files for name in nfc_batch_names):
                    logger.debug(f"Batch {batch_num} already processed, skipping OCR")
                    for _ in batch_paths:
                        bar.update()
                    continue

                # Separate batch into: already-done (bar update + skip), needs-OCR
                needs_ocr: List[tuple] = []  # (path, pil_image) that need processing
                for path in batch_paths:
                    nfc_name = _nfc(path.name)
                    if nfc_name in processed_files:
                        bar.update()  # already done — count it, skip OCR
                        continue
                    try:
                        image = self.image_repository.read(path)
                        needs_ocr.append((path, image))
                    except Exception as e:
                        logger.warning(f"Failed to load image {path.name}: {e}")
                        errors.append(
                            {
                                "file": path.name,
                                "error": f"Failed to load: {e}",
                            }
                        )
                        bar.update()  # failed-load — count it, skip OCR

                if not needs_ocr:
                    continue

                # OCR batch (may fail completely — OCR-level error)
                try:
                    batch_ocr_results = self.ocr_service.extract_lines_batch(
                        [img for _, img in needs_ocr]
                    )
                except Exception as e:
                    logger.error(f"Batch {batch_num} OCR failed: {e}")
                    for path, _ in needs_ocr:
                        errors.append(
                            {
                                "file": path.name,
                                "error": f"Batch OCR error: {e}",
                            }
                        )
                        bar.update()
                    continue

                # Process results: per-image parse — 1:1 zip, no index desync
                for (path, pil_image), lines in zip(needs_ocr, batch_ocr_results):
                    nfc_name = _nfc(path.name)
                    try:
                        logger.info(f"Processing: {path.name}")
                        logger.debug(f"Extracted {len(lines)} lines from {path.name}")

                        # Parse table (may fail — parse-level error)
                        entries = self.table_parser.parse(
                            lines, pil_image.width, source_image=nfc_name
                        )
                        all_entries.extend(entries)
                        processed += 1

                        # Mark checkpoint after successful processing
                        if resume:
                            self.checkpoint_repository.mark_done(nfc_name)
                            processed_files.add(nfc_name)

                        logger.info(f"Parsed {len(entries)} entries from {path.name}")

                    except Exception as e:
                        logger.warning(f"Failed to parse {path.name}: {e}")
                        errors.append(
                            {
                                "file": path.name,
                                "error": str(e),
                            }
                        )

                    bar.update()

        # Deduplicate entries by MCC code (keep longer description)
        unique_entries = self._deduplicate_entries(all_entries)

        # Sort by MCC code
        unique_entries.sort(key=lambda e: e.mcc.zfill(4) if e.mcc.isdigit() else e.mcc)

        logger.info(
            f"Total entries: {len(unique_entries)} "
            f"(parsed={sum(1 for e in unique_entries if not e.unparsed)}, "
            f"unparsed={sum(1 for e in unique_entries if e.unparsed)})"
        )

        # Save to JSON
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

    def _group_into_batches(self, paths: List[Path]) -> List[List[Path]]:
        """
        Group image paths into batches of BATCH_SIZE.

        Args:
            paths: List of image paths.

        Returns:
            List of batches, each containing up to BATCH_SIZE paths.
        """
        batches: List[List[Path]] = []
        for i in range(0, len(paths), self.BATCH_SIZE):
            batches.append(paths[i : i + self.BATCH_SIZE])
        return batches

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
