"""
MCC Parser Service implementation.
"""

import re
from typing import Dict, List, Optional

from loguru import logger

from app.models.mcc_entry import MCCEntry


class MCCParserService:
    """
    Service for parsing table rows into MCCEntry objects.
    """

    def parse(self, rows: List[Dict[str, str]], source: str) -> List[MCCEntry]:
        """
        Parse table rows into MCCEntry objects.

        Args:
            rows: List of row dictionaries with keys: mcc, title_description, included, similar_merchants.
            source: Source image filename for tracking.

        Returns:
            List of MCCEntry objects.
        """
        entries: List[MCCEntry] = []

        for row in rows:
            entry = self._parse_row(row, source)
            if entry:
                entries.append(entry)

        logger.info(f"Parsed {len(entries)} MCC entries from {source}")
        return entries

    def _parse_row(self, row: Dict[str, str], source: str) -> MCCEntry:
        """
        Parse a single row dictionary into MCCEntry.

        Args:
            row: Dictionary with keys: mcc, title_description, included, similar_merchants.
            source: Source image filename.

        Returns:
            MCCEntry object.
        """
        mcc = row.get("mcc", "").strip()
        title_description = row.get("title_description", "").strip()
        included = row.get("included", "").strip()
        similar_merchants_text = row.get("similar_merchants", "").strip()

        # Validate MCC: must be 4 digits if present
        if mcc and not (mcc.isdigit() and len(mcc) == 4):
            logger.warning(f"Invalid MCC code '{mcc}' in {source}, marking as unparsed")
            return self._unparsed_entry(source, reason=f"invalid mcc: {mcc}")

        # Parse similar_merchants by comma/newline
        similar_merchants = self._parse_similar_merchants(similar_merchants_text)

        # If MCC is empty, mark as unparsed
        if not mcc:
            logger.debug(f"Empty MCC in row from {source}, marking as unparsed")
            return self._unparsed_entry(
                source,
                reason="empty mcc",
                raw_content={
                    "title_description": title_description,
                    "included": included,
                    "similar_merchants": similar_merchants_text,
                },
            )

        try:
            return MCCEntry(
                mcc=mcc,
                title_description=title_description,
                included=included,
                similar_merchants=similar_merchants,
                source_image=source,
                unparsed=False,
            )
        except ValueError as e:
            logger.warning(f"Failed to create MCC entry for {mcc}: {e}")
            return self._unparsed_entry(source, reason=str(e))

    def _parse_similar_merchants(self, text: str) -> List[str]:
        """
        Parse similar_merchants text by splitting on comma or newline.

        Args:
            text: Raw similar_merchants text.

        Returns:
            List of merchant names.
        """
        if not text:
            return []

        # Split by comma or newline
        parts = re.split(r"[,\n]+", text)
        merchants = [p.strip() for p in parts if p.strip()]

        return merchants

    def _unparsed_entry(
        self, source: str, reason: str, raw_content: Optional[Dict[str, str]] = None
    ) -> MCCEntry:
        """
        Create an unparsed MCC entry.

        Args:
            source: Source image filename.
            reason: Reason for unparsed status.
            raw_content: Optional raw content for debugging.

        Returns:
            MCCEntry with unparsed=True.
        """
        return MCCEntry(
            mcc="",
            title_description=raw_content.get("title_description", "") if raw_content else "",
            included=raw_content.get("included", "") if raw_content else "",
            similar_merchants=self._parse_similar_merchants(
                raw_content.get("similar_merchants", "") if raw_content else ""
            ),
            source_image=source,
            unparsed=True,
        )
