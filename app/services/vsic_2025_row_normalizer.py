"""
VSIC 2025 Row Normalizer service.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger


@dataclass
class NormalizedRow:
    """Normalized row data with level detection."""

    is_level_4: bool
    """True if this row contains a level 4 entry."""

    code: Optional[str]
    """VSIC code (level 4 or 5) as string, or None if invalid."""

    title: str
    """Category title."""

    level_4_code: Optional[str]
    """Level 4 code if this is a level 5 child row."""

    extra_level_5: Optional[str]
    """Additional level 5 code when row has both level 4 and level 5."""


def normalize_row_2025(row: Dict[str, Any]) -> Optional[NormalizedRow]:
    """
    Normalize a raw Excel row for VSIC 2025 format.

    Detects whether row contains:
    - Level 4 entry: Cấp 4 has value
    - Level 5 child: Cấp 4 is None, Cấp 5 has value
    - Invalid: Neither Cấp 4 nor Cấp 5 has value

    Args:
        row: Dictionary with keys like 'Cấp 1', 'Cấp 2', 'Cấp 3',
             'Cấp 4', 'Cấp 5', 'Tên ngành'.

    Returns:
        NormalizedRow if row contains valid data, None otherwise.
    """
    cap_4 = row.get("Cấp 4")
    cap_5 = row.get("Cấp 5")
    title = row.get("Tên ngành", "")

    has_cap_4 = cap_4 is not None and str(cap_4).strip()
    has_cap_5 = cap_5 is not None and str(cap_5).strip()

    # Skip rows with neither level 4 nor level 5 codes
    if not has_cap_4 and not has_cap_5:
        return None

    # Normalize title
    normalized_title = str(title).strip() if title else ""

    if has_cap_4:
        # This is a level 4 entry
        # Level 4 code is from Cấp 4 column
        level_4_code = normalize_code(cap_4)

        if not level_4_code:
            logger.warning(f"Empty level 4 code after normalization: {cap_4!r}")
            return None

        # Check if this row ALSO has a level 5 code (child in same row)
        extra_level_5 = None
        if has_cap_5:
            extra_level_5 = normalize_code(cap_5)

        return NormalizedRow(
            is_level_4=True,
            code=level_4_code,
            title=normalized_title,
            level_4_code=None,  # Not a child row
            extra_level_5=extra_level_5,
        )

    else:
        # This is a level 5 child entry
        level_5_code = normalize_code(cap_5)

        if not level_5_code:
            logger.warning(f"Empty level 5 code after normalization: {cap_5!r}")
            return None

        return NormalizedRow(
            is_level_4=False,
            code=level_5_code,
            title=normalized_title,
            level_4_code=None,  # Will be set by parser based on current level 4
            extra_level_5=None,
        )


def normalize_code(raw_value: Any) -> Optional[str]:
    """
    Normalize a VSIC code value to string format.

    - Preserves the code as-is from source (no zero-padding)
    - Converts numeric values to string without losing leading zeros
    - Handles float values (e.g., 111.0 -> "111")

    Args:
        raw_value: Raw value from Excel cell.

    Returns:
        Normalized code string, or None if invalid.
    """
    if raw_value is None:
        return None

    raw_str = str(raw_value).strip()

    if not raw_str:
        return None

    # Handle numeric values that might be floats
    try:
        # Try to parse as float first
        float_val = float(raw_str)
        # If it's a whole number, convert to int then str
        if float_val == int(float_val):
            return str(int(float_val))
        return raw_str
    except (ValueError, TypeError):
        # Not a number, return as-is
        return raw_str
