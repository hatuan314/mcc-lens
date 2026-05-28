"""
Unit tests for VSIC 2025 Parser Service.
"""

import pytest

from app.models.vsic_2025_entry import Vsic2025Entry, VsicLevel5Child
from app.services.vsic_2025_parser_service import Vsic2025ParserService


@pytest.fixture
def parser() -> Vsic2025ParserService:
    return Vsic2025ParserService()


class TestParseRowsLevelDetection:
    """Tests for level detection in parse_rows."""

    def test_empty_rows_returns_empty_list(self, parser: Vsic2025ParserService) -> None:
        assert parser.parse_rows([]) == []

    def test_single_level_4_entry(self, parser: Vsic2025ParserService) -> None:
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert entries[0].code == "111"
        assert entries[0].title == "Trồng lúa"
        assert entries[0].children_level5 == []

    def test_multiple_level_4_entries(self, parser: Vsic2025ParserService) -> None:
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 4": 112, "Tên ngành": "Trồng ngô"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 2
        assert entries[0].code == "111"
        assert entries[1].code == "112"


class TestParseRowsChildGrouping:
    """Tests for grouping level 5 children under level 4 parents."""

    def test_level_5_grouped_under_level_4(self, parser: Vsic2025ParserService) -> None:
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1110, "Tên ngành": "Lúa hạt"},
            {"Cấp 5": 1111, "Tên ngành": "Lúa gạo"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert len(entries[0].children_level5) == 2
        assert entries[0].children_level5[0].code == "1110"
        assert entries[0].children_level5[1].code == "1111"

    def test_multiple_level_4_with_children(
        self, parser: Vsic2025ParserService
    ) -> None:
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1110, "Tên ngành": "Lúa hạt"},
            {"Cấp 4": 112, "Tên ngành": "Trồng ngô"},
            {"Cấp 5": 1120, "Tên ngành": "Ngô vàng"},
            {"Cấp 5": 1121, "Tên ngành": "Ngô đen"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 2
        assert len(entries[0].children_level5) == 1
        assert len(entries[1].children_level5) == 2
        assert entries[1].children_level5[0].code == "1120"
        assert entries[1].children_level5[1].code == "1121"

    def test_level_4_without_children(self, parser: Vsic2025ParserService) -> None:
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 4": 112, "Tên ngành": "Trồng ngô"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 2
        assert entries[0].children_level5 == []
        assert entries[1].children_level5 == []


class TestParseRowsInlineChild:
    """Tests for handling rows with both level 4 and level 5 (inline children)."""

    def test_inline_level_5_child(self, parser: Vsic2025ParserService) -> None:
        """Row with both Cấp 4 and Cấp 5 should create entry with inline child."""
        rows = [{"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert entries[0].code == "111"
        assert len(entries[0].children_level5) == 1
        assert entries[0].children_level5[0].code == "1110"

    def test_inline_child_plus_subsequent_children(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Inline child should be added before subsequent children."""
        rows = [
            {"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1111, "Tên ngành": "Lúa gạo"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert len(entries[0].children_level5) == 2
        assert entries[0].children_level5[0].code == "1110"
        assert entries[0].children_level5[1].code == "1111"

    def test_inline_child_uses_same_title(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Inline child should use the same title as the parent row."""
        rows = [{"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        assert entries[0].children_level5[0].title == "Trồng lúa"


class TestParseRowsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_level_5_without_parent_is_skipped(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Level 5 row before any level 4 should be skipped."""
        rows = [
            {"Cấp 5": 1110, "Tên ngành": "Orphan child"},
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert entries[0].code == "111"
        assert entries[0].children_level5 == []

    def test_empty_rows_between_entries(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Empty rows (no Cấp 4/5) should be skipped."""
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 1": "A", "Tên ngành": "Header row"},
            {"Cấp 5": 1110, "Tên ngành": "Lúa hạt"},
        ]
        entries = parser.parse_rows(rows)

        assert len(entries) == 1
        assert len(entries[0].children_level5) == 1

    def test_float_codes_normalized(self, parser: Vsic2025ParserService) -> None:
        """Float codes (e.g., 111.0) should be normalized to string."""
        rows = [
            {"Cấp 4": 111.0, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1110.0, "Tên ngành": "Lúa hạt"},
        ]
        entries = parser.parse_rows(rows)

        assert entries[0].code == "111"
        assert entries[0].children_level5[0].code == "1110"

    def test_string_codes(self, parser: Vsic2025ParserService) -> None:
        """String codes should work correctly."""
        rows = [
            {"Cấp 4": "111", "Tên ngành": "Trồng lúa"},
            {"Cấp 5": "1110", "Tên ngành": "Lúa hạt"},
        ]
        entries = parser.parse_rows(rows)

        assert entries[0].code == "111"
        assert entries[0].children_level5[0].code == "1110"

    def test_returns_vsic_2025_entry_objects(
        self, parser: Vsic2025ParserService
    ) -> None:
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        assert all(isinstance(e, Vsic2025Entry) for e in entries)

    def test_children_are_vsic_level5_child_objects(
        self, parser: Vsic2025ParserService
    ) -> None:
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1110, "Tên ngành": "Lúa hạt"},
        ]
        entries = parser.parse_rows(rows)

        assert all(
            isinstance(c, VsicLevel5Child) for c in entries[0].children_level5
        )


class TestParseRowsOutputSchema:
    """Tests verifying output schema compliance."""

    def test_output_has_no_level_field(self, parser: Vsic2025ParserService) -> None:
        """Output should not contain 'level' field per requirements."""
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        entry_dict = entries[0].model_dump()
        assert "level" not in entry_dict

    def test_output_has_no_parent_code_field(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Output should not contain 'parent_code' field per requirements."""
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        entry_dict = entries[0].model_dump()
        assert "parent_code" not in entry_dict

    def test_output_has_no_description_field(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Output should not contain 'description' field per requirements."""
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        entry_dict = entries[0].model_dump()
        assert "description" not in entry_dict

    def test_output_has_required_fields(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Output should have code, title, and children_level5."""
        rows = [{"Cấp 4": 111, "Tên ngành": "Trồng lúa"}]
        entries = parser.parse_rows(rows)

        entry_dict = entries[0].model_dump()
        assert "code" in entry_dict
        assert "title" in entry_dict
        assert "children_level5" in entry_dict

    def test_child_has_required_fields_only(
        self, parser: Vsic2025ParserService
    ) -> None:
        """Children should only have code and title."""
        rows = [
            {"Cấp 4": 111, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1110, "Tên ngành": "Lúa hạt"},
        ]
        entries = parser.parse_rows(rows)

        child_dict = entries[0].children_level5[0].model_dump()
        assert set(child_dict.keys()) == {"code", "title"}
