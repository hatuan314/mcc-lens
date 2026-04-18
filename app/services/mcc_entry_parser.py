"""
MCC Entry Parser — parses raw entry dicts into MCCEntry objects.
"""

import re
from typing import Any, Dict

from loguru import logger

from app.models.mcc_entry import MCCEntry, SimilarMerchant


class MCCEntryParser:
    """
    Parses a raw entry dict from EntryGrouper into an MCCEntry.

    Logic:
        - First _desc_lines → title; rest → description.
        - Parse _similar_lines into list[SimilarMerchant] with title continuation.
        - Filter _included_lines (>2 chars) → included_in_mcc.
        - Set unparsed=True when mcc is empty.
    """

    SIMILAR_MERCHANT_PATTERN = re.compile(r"^(\d{4})\s*[–\-]\s*(.+)$")

    def parse(self, raw: Dict[str, Any], source_image: str) -> MCCEntry:
        """
        Parse a raw entry dictionary into an MCCEntry.

        Args:
            raw: Raw entry dict from EntryGrouper.
            source_image: Source image filename for tracking.

        Returns:
            MCCEntry object.
        """
        mcc = raw.get("mcc", "")
        desc_lines = raw.get("_desc_lines", [])
        included_lines = raw.get("_included_lines", [])
        similar_lines = raw.get("_similar_lines", [])

        # Title = first desc line; description = rest
        title = desc_lines[0] if desc_lines else None
        description = " ".join(desc_lines[1:]).strip() if len(desc_lines) > 1 else None

        # Filter included lines (>2 chars)
        included_in_mcc = [line for line in included_lines if len(line) > 2]

        # Parse similar merchants with title continuation
        similar_merchants = self._parse_similar_merchants(similar_lines)

        # Mark unparsed when mcc is empty
        unparsed = mcc == ""

        if unparsed:
            logger.debug(f"Empty MCC in entry from {source_image}, marking as unparsed")

        return MCCEntry(
            mcc=mcc,
            title=title,
            description=description if description else None,
            included_in_mcc=included_in_mcc,
            similar_merchants=similar_merchants,
            source_image=source_image,
            unparsed=unparsed,
        )

    def _parse_similar_merchants(self, lines: list[str]) -> list[SimilarMerchant]:
        """
        Parse similar merchant lines into SimilarMerchant objects.

        Handles title continuation: if a line doesn't match the MCC pattern
        and there's a pending merchant, append to its title.

        Args:
            lines: List of raw similar merchant text lines.

        Returns:
            List of SimilarMerchant objects.
        """
        merchants: list[SimilarMerchant] = []
        pending: SimilarMerchant | None = None

        for line in lines:
            parsed = self._parse_single_merchant(line)
            if parsed:
                if pending:
                    merchants.append(pending)
                pending = parsed
            elif pending:
                # Continuation of previous title (e.g., "Supplies Store" after cut)
                pending = SimilarMerchant(
                    mcc=pending.mcc,
                    title=pending.title + " " + line.strip(),
                )

        if pending:
            merchants.append(pending)

        return merchants

    def _parse_single_merchant(self, text: str) -> SimilarMerchant | None:
        """
        Parse a line like "5995 – Pet Shops" into SimilarMerchant.

        Args:
            text: Raw text line.

        Returns:
            SimilarMerchant or None if no match.
        """
        match = self.SIMILAR_MERCHANT_PATTERN.match(text.strip())
        if match:
            return SimilarMerchant(mcc=match.group(1), title=match.group(2).strip())
        return None
