"""
Unit tests for VsicParserService.
"""

import pytest

from app.models.vsic_entry import VsicEntry
from app.services.vsic_parser_service import VsicParserService


@pytest.fixture
def parser() -> VsicParserService:
    return VsicParserService()


class TestExtractCode:
    def test_integer_code(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề ": 1110, "Tên ngành": "Trồng lúa"}
        assert parser._extract_code(row) == "1110"

    def test_float_code(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề ": 1110.0, "Tên ngành": "Trồng lúa"}
        assert parser._extract_code(row) == "1110"

    def test_string_integer_code(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề ": "1110", "Tên ngành": "Trồng lúa"}
        assert parser._extract_code(row) == "1110"

    def test_code_without_trailing_space_key(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề": 1120, "Tên ngành": "Trồng ngô"}
        assert parser._extract_code(row) == "1120"

    def test_non_integer_code_returns_empty(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề ": "ABC", "Tên ngành": "Invalid"}
        assert parser._extract_code(row) == ""

    def test_none_code_returns_empty(self, parser: VsicParserService) -> None:
        row = {"Mã ngành nghề ": None, "Tên ngành": "Empty"}
        assert parser._extract_code(row) == ""

    def test_missing_key_returns_empty(self, parser: VsicParserService) -> None:
        row = {"Other": "value"}
        assert parser._extract_code(row) == ""


class TestExtractTitle:
    def test_vn_header(self, parser: VsicParserService) -> None:
        row = {"Tên ngành": "Trồng lúa"}
        assert parser._extract_title(row) == "Trồng lúa"

    def test_en_header(self, parser: VsicParserService) -> None:
        row = {"Title": "Grow rice"}
        assert parser._extract_title(row) == "Grow rice"

    def test_missing_title_returns_empty(self, parser: VsicParserService) -> None:
        row = {"Other": "value"}
        assert parser._extract_title(row) == ""

    def test_title_whitespace_stripped(self, parser: VsicParserService) -> None:
        row = {"Tên ngành": "  Trồng lúa  "}
        assert parser._extract_title(row) == "Trồng lúa"


class TestParseRows:
    def test_digits_4(self, parser: VsicParserService) -> None:
        rows = [{"Mã ngành nghề ": 1110, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert entries[0].code == "1110"
        assert entries[0].digits == 4

    def test_digits_5(self, parser: VsicParserService) -> None:
        rows = [{"Mã ngành nghề ": 11100, "Tên ngành": "Trồng lúa chi tiết"}]
        entries = parser.parse_rows(rows)

        assert entries[0].digits == 5
        assert entries[0].code == "11100"

    def test_empty_code_row_skipped(self, parser: VsicParserService) -> None:
        rows = [
            {"Mã ngành nghề ": None, "Tên ngành": "Empty"},
            {"Mã ngành nghề ": 1110, "Tên ngành": "Valid"},
        ]
        entries = parser.parse_rows(rows)
        assert len(entries) == 1
        assert entries[0].code == "1110"

    def test_non_integer_code_row_skipped(self, parser: VsicParserService) -> None:
        rows = [
            {"Mã ngành nghề ": "ABC", "Tên ngành": "Invalid"},
            {"Mã ngành nghề ": 1110, "Tên ngành": "Valid"},
        ]
        entries = parser.parse_rows(rows)
        assert len(entries) == 1

    def test_empty_rows_list(self, parser: VsicParserService) -> None:
        assert parser.parse_rows([]) == []

    def test_returns_vsic_entry_objects(self, parser: VsicParserService) -> None:
        rows = [{"Mã ngành nghề ": 1110, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)
        assert all(isinstance(e, VsicEntry) for e in entries)

    def test_title_stored_correctly(self, parser: VsicParserService) -> None:
        rows = [{"Mã ngành nghề ": 1110, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)
        assert entries[0].title == "Trồng lúa"

    def test_multiple_rows(self, parser: VsicParserService) -> None:
        rows = [
            {"Mã ngành nghề ": 1110, "Tên ngành": "Row A"},
            {"Mã ngành nghề ": 1120, "Tên ngành": "Row B"},
            {"Mã ngành nghề ": 11100, "Tên ngành": "Row C"},
        ]
        entries = parser.parse_rows(rows)
        assert len(entries) == 3
        assert entries[2].digits == 5
