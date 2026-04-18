"""
Entry Grouper — groups classified OCR lines into raw MCC entries.
"""

import re
from typing import Any, Dict, List

from app.models.ocr_line import OCRLine


class EntryGrouper:
    """
    Groups classified OCR lines into raw entries.

    A new entry is triggered when text matches ^\\d{4}$ in the "mcc" column.
    """

    MCC_PATTERN = re.compile(r"^\d{4}$")

    def group(self, classified: List[tuple]) -> List[Dict[str, Any]]:
        """
        Group classified lines into raw entries.

        Args:
            classified: List of (OCRLine, column_name) tuples.

        Returns:
            List of raw entry dicts with keys:
                mcc, _desc_lines, _included_lines, _similar_lines.
        """
        entries: List[Dict[str, Any]] = []
        current: Dict[str, Any] | None = None

        for line, col in classified:
            text = line.text.strip()

            if col == "mcc" and self.MCC_PATTERN.match(text):
                # Start new entry
                if current is not None:
                    entries.append(current)
                current = {
                    "mcc": text,
                    "_desc_lines": [],
                    "_included_lines": [],
                    "_similar_lines": [],
                }
            elif current is not None:
                if col == "desc":
                    current["_desc_lines"].append(text)
                elif col == "included":
                    current["_included_lines"].append(text)
                elif col == "similar":
                    current["_similar_lines"].append(text)

        # Don't lose the last entry
        if current is not None:
            entries.append(current)

        return entries
