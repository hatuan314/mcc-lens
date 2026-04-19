"""
Integration tests for MCCTableParserService.

Tests the orchestration of ColumnClassifier → EntryGrouper → MCCEntryParser.
"""

import pytest

from app.models.ocr_line import OCRLine
from app.services.mcc_table_parser_service import MCCTableParserService


@pytest.fixture
def service() -> MCCTableParserService:
    return MCCTableParserService()


def line(text: str, x_ratio: float, image_width: int = 1000) -> OCRLine:
    """Build an OCRLine whose x1 falls in the column for the given ratio."""
    x1 = x_ratio * image_width
    return OCRLine(text=text, bbox=[x1, 0.0, x1 + 10.0, 20.0], confidence=1.0)


class TestMCCTableParserService:
    def test_full_pipeline_happy_path(self, service: MCCTableParserService) -> None:
        # Ratios: mcc=0-12%, desc=12-46%, included=46-64%, similar=64-100%
        lines = [
            line("5812", x_ratio=0.05),  # mcc
            line("Eating Places", x_ratio=0.20),  # desc
            line("Restaurants and cafes serving food.", x_ratio=0.20),  # desc
            line("Cafes", x_ratio=0.50),  # included
            line("Food Courts", x_ratio=0.50),  # included
            line("5814 – Fast Food", x_ratio=0.70),  # similar
        ]
        entries = service.parse(lines, image_width=1000, source_image="p1.jpg")

        assert len(entries) == 1
        e = entries[0]
        assert e.mcc == "5812"
        assert e.title == "Eating Places"
        assert e.description == "Restaurants and cafes serving food."
        assert e.included_in_mcc == ["Cafes", "Food Courts"]
        assert len(e.similar_merchants) == 1
        assert e.similar_merchants[0].mcc == "5814"
        assert e.source_image == "p1.jpg"
        assert e.unparsed is False

    def test_multiple_entries(self, service: MCCTableParserService) -> None:
        lines = [
            line("5812", x_ratio=0.05),
            line("Eating Places", x_ratio=0.20),
            line("5814", x_ratio=0.05),
            line("Fast Food", x_ratio=0.20),
        ]
        entries = service.parse(lines, image_width=1000)
        assert len(entries) == 2
        assert entries[0].mcc == "5812"
        assert entries[1].mcc == "5814"

    def test_empty_lines_returns_empty(self, service: MCCTableParserService) -> None:
        assert service.parse([], image_width=1000) == []

    def test_lines_before_first_mcc_ignored(
        self, service: MCCTableParserService
    ) -> None:
        lines = [
            line("Header", x_ratio=0.20),  # desc, before any MCC
            line("5812", x_ratio=0.05),
            line("Eating Places", x_ratio=0.20),
        ]
        entries = service.parse(lines, image_width=1000)
        assert len(entries) == 1
        assert entries[0].title == "Eating Places"

    def test_default_source_image_empty(self, service: MCCTableParserService) -> None:
        lines = [
            line("5812", x_ratio=0.05),
            line("A", x_ratio=0.20),
        ]
        entries = service.parse(lines, image_width=1000)
        assert entries[0].source_image == ""
