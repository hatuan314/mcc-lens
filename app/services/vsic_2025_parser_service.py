"""
VSIC 2025 Parser Service implementation.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.vsic_2025_entry import Vsic2025Entry, VsicLevel5Child
from app.services.vsic_2025_row_normalizer import normalize_row_2025


class Vsic2025ParserService:
    """
    Service for parsing raw Excel rows into nested Vsic2025Entry objects.

    Groups level 5 children under their parent level 4 entries.
    """

    def parse_rows(self, rows: List[Dict[str, Any]]) -> List[Vsic2025Entry]:
        """
        Parse raw Excel rows into Vsic2025Entry objects with nested children.

        Args:
            rows: List of row dictionaries from Excel.

        Returns:
            List of Vsic2025Entry (level 4 entries with children_level5 arrays).
        """
        entries: List[Vsic2025Entry] = []
        current_level_4: Optional[Vsic2025Entry] = None
        skipped_rows = 0

        for row_idx, row in enumerate(rows):
            normalized = normalize_row_2025(row)

            if normalized is None:
                skipped_rows += 1
                continue

            if normalized.is_level_4:
                # Start a new level 4 entry
                current_level_4 = Vsic2025Entry(
                    code=normalized.code,
                    title=normalized.title,
                    children_level5=[],
                )
                entries.append(current_level_4)
                logger.debug(
                    f"Row {row_idx}: Created level 4 entry {normalized.code}"
                )

                # Handle rows with both level 4 and level 5 in same row
                if normalized.extra_level_5:
                    child = VsicLevel5Child(
                        code=normalized.extra_level_5,
                        title=normalized.title,  # Use same title or could be modified
                    )
                    current_level_4.children_level5.append(child)
                    logger.debug(
                        f"Row {row_idx}: Added inline level 5 child "
                        f"{normalized.extra_level_5} to {normalized.code}"
                    )

            else:
                # This is a level 5 child - add to current level 4
                if current_level_4 is None:
                    logger.warning(
                        f"Row {row_idx}: Level 5 entry {normalized.code} "
                        f"without parent level 4 - skipping"
                    )
                    skipped_rows += 1
                    continue

                child = VsicLevel5Child(
                    code=normalized.code,
                    title=normalized.title,
                )
                current_level_4.children_level5.append(child)
                logger.debug(
                    f"Row {row_idx}: Added level 5 child {normalized.code} "
                    f"to {current_level_4.code}"
                )

        logger.info(
            f"Parsed {len(entries)} level 4 entries with "
            f"{sum(len(e.children_level5) for e in entries)} total level 5 children. "
            f"Skipped {skipped_rows} rows."
        )

        return entries
