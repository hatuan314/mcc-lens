"""
MCC Table Parser Service — orchestrates the full table parsing pipeline.
"""

from typing import List

from loguru import logger

from app.models.mcc_entry import MCCEntry
from app.models.ocr_line import OCRLine
from app.services.column_classifier import ColumnClassifier
from app.services.entry_grouper import EntryGrouper
from app.services.mcc_entry_parser import MCCEntryParser


class MCCTableParserService:
    """
    Orchestrator for the MCC table parsing pipeline.

    Pipeline: ColumnClassifier → EntryGrouper → MCCEntryParser
    """

    def __init__(
        self,
        column_classifier: ColumnClassifier | None = None,
        entry_grouper: EntryGrouper | None = None,
        entry_parser: MCCEntryParser | None = None,
    ) -> None:
        self.column_classifier = column_classifier or ColumnClassifier()
        self.entry_grouper = entry_grouper or EntryGrouper()
        self.entry_parser = entry_parser or MCCEntryParser()

    def parse(
        self,
        lines: List[OCRLine],
        image_width: int,
        source_image: str = "",
    ) -> List[MCCEntry]:
        """
        Parse OCR lines into a list of MCCEntry objects.

        Args:
            lines: List of OCRLine from OCRService.
            image_width: Width of the source image in pixels.
            source_image: Source image filename for provenance.

        Returns:
            List of MCCEntry objects.
        """
        # Step 1: Classify each line into a column
        classified = [
            (line, self.column_classifier.classify(line, image_width))
            for line in lines
        ]

        # Step 2: Group classified lines into raw entries
        raw_entries = self.entry_grouper.group(classified)
        logger.debug(f"Grouped into {len(raw_entries)} raw entries")

        # Step 3: Parse each raw entry into MCCEntry
        entries = [
            self.entry_parser.parse(raw, source_image=source_image)
            for raw in raw_entries
        ]

        logger.debug(f"Parsed {len(entries)} MCC entries")
        return entries
