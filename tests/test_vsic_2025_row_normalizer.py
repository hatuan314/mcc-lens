"""
Unit tests for VSIC 2025 Row Normalizer.
"""

import pytest

from app.services.vsic_2025_row_normalizer import (
    NormalizedRow,
    normalize_row_2025,
    normalize_code,
)


class TestNormalizeCode:
    """Tests for normalize_code function."""

    def test_none_returns_none(self) -> None:
        assert normalize_code(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert normalize_code("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert normalize_code("   ") is None

    def test_integer_value(self) -> None:
        assert normalize_code(111) == "111"

    def test_float_whole_number(self) -> None:
        assert normalize_code(111.0) == "111"

    def test_float_with_decimals(self) -> None:
        assert normalize_code(111.5) == "111.5"

    def test_string_integer(self) -> None:
        assert normalize_code("111") == "111"

    def test_string_float_whole_number(self) -> None:
        assert normalize_code("111.0") == "111"

    def test_non_numeric_string(self) -> None:
        assert normalize_code("ABC") == "ABC"

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert normalize_code("  111  ") == "111"

    def test_level_4_code_four_digits(self) -> None:
        assert normalize_code(1110) == "1110"

    def test_level_5_code_five_digits(self) -> None:
        assert normalize_code(11100) == "11100"


class TestNormalizeRow2025:
    """Tests for normalize_row_2025 function."""

    def test_row_without_cap4_or_cap5_returns_none(self) -> None:
        row = {"Cấp 1": "A", "Cấp 2": "01", "Tên ngành": "Some title"}
        assert normalize_row_2025(row) is None

    def test_row_with_cap4_only(self) -> None:
        row = {"Cấp 4": 111, "Tên ngành": "Trồng lúa"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.is_level_4 is True
        assert result.code == "111"
        assert result.title == "Trồng lúa"
        assert result.extra_level_5 is None

    def test_row_with_cap5_only(self) -> None:
        row = {"Cấp 5": 1110, "Tên ngành": "Trồng lúa chi tiết"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.is_level_4 is False
        assert result.code == "1110"
        assert result.title == "Trồng lúa chi tiết"

    def test_row_with_both_cap4_and_cap5(self) -> None:
        """Row with both level 4 and level 5 (inline child)."""
        row = {"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.is_level_4 is True
        assert result.code == "111"
        assert result.extra_level_5 == "1110"
        assert result.title == "Trồng lúa"

    def test_cap4_as_float(self) -> None:
        row = {"Cấp 4": 111.0, "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.code == "111"

    def test_cap5_as_string(self) -> None:
        row = {"Cấp 5": "1110", "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.code == "1110"

    def test_empty_cap4_string(self) -> None:
        """Empty string should be treated as no value."""
        row = {"Cấp 4": "", "Cấp 5": 1110, "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.is_level_4 is False
        assert result.code == "1110"

    def test_whitespace_cap4(self) -> None:
        """Whitespace-only should be treated as no value."""
        row = {"Cấp 4": "   ", "Cấp 5": 1110, "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.is_level_4 is False

    def test_missing_title(self) -> None:
        row = {"Cấp 4": 111}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.title == ""

    def test_title_with_whitespace(self) -> None:
        row = {"Cấp 4": 111, "Tên ngành": "  Trồng lúa  "}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.title == "Trồng lúa"

    def test_level_4_code_level_4_code_field_is_none(self) -> None:
        """For level 4 rows, level_4_code should be None (not a child)."""
        row = {"Cấp 4": 111, "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.level_4_code is None

    def test_level_5_code_level_4_code_field_is_none(self) -> None:
        """For level 5 rows, level_4_code is None (set by parser)."""
        row = {"Cấp 5": 1110, "Tên ngành": "Test"}
        result = normalize_row_2025(row)

        assert result is not None
        assert result.level_4_code is None

    def test_completely_empty_row(self) -> None:
        row = {}
        assert normalize_row_2025(row) is None

    def test_row_with_none_values(self) -> None:
        row = {"Cấp 4": None, "Cấp 5": None, "Tên ngành": None}
        assert normalize_row_2025(row) is None
