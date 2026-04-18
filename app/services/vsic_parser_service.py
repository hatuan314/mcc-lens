"""
VSIC Parser Service implementation.
"""

from typing import Any, Dict, List

from loguru import logger

from app.models.vsic_entry import VsicEntry


class VsicParserService:
    """
    Service for parsing raw Excel rows into VsicEntry objects.
    """

    def parse_rows(self, rows: List[Dict[str, Any]]) -> List[VsicEntry]:
        """
        Parse raw Excel rows into VsicEntry objects.

        Args:
            rows: List of row dictionaries from Excel.

        Returns:
            List of VsicEntry with code (string) and digits (4 or 5).
        """
        entries = []

        for row in rows:
            code = self._extract_code(row)
            if not code:
                continue

            title = self._extract_title(row)
            digits = len(code)

            entries.append(VsicEntry(code=code, title=title, digits=digits))

        return entries

    def _extract_code(self, row: Dict[str, Any]) -> str:
        """Extract and normalize VSIC code from row as string."""
        for key in ["Mã ngành nghề ", "Mã ngành nghề", "Code", "code", "Mã", "mã"]:
            if key in row and row[key] is not None:
                raw = row[key]
                try:
                    return str(int(float(str(raw).strip())))
                except (ValueError, TypeError):
                    logger.warning(f"Skipping non-integer code: {raw!r}")
                    return ""
        return ""

    def _extract_title(self, row: Dict[str, Any]) -> str:
        """Extract title from row."""
        for key in ["Tên ngành", "Title", "title", "Tên", "tên"]:
            if key in row and row[key]:
                return str(row[key]).strip()
        return ""
