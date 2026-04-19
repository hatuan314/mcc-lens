"""Service for validating MCC codes returned by LLM."""

from typing import List

from loguru import logger


class MccCodeValidator:
    """
    Validates that MCC codes returned by LLM exist in the valid list.
    Falls back to top-1 embedding if LLM hallucinates.
    """

    def __init__(self, valid_mcc_codes: List[str]) -> None:
        """
        Initialize validator with list of valid MCC codes.

        Args:
            valid_mcc_codes: List of valid 4-character MCC codes.
        """
        self.valid_mcc_codes = set(valid_mcc_codes)

    def validate(self, mcc_code: str, fallback_mcc_code: str) -> str:
        """
        Validate an MCC code, falling back if invalid.

        Args:
            mcc_code: MCC code to validate.
            fallback_mcc_code: Fallback code (top-1 from embedding).

        Returns:
            Valid MCC code (either original or fallback).
        """
        if mcc_code in self.valid_mcc_codes:
            return mcc_code

        logger.warning(
            f"LLM returned invalid MCC code '{mcc_code}', falling back to "
            f"'{fallback_mcc_code}'"
        )

        if fallback_mcc_code in self.valid_mcc_codes:
            return fallback_mcc_code

        logger.error(f"Fallback MCC code '{fallback_mcc_code}' is also invalid")
        return ""
