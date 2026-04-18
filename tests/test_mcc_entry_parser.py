"""
Unit tests for MCCEntryParser.
"""

import pytest

from app.models.mcc_entry import MCCEntry, SimilarMerchant
from app.services.mcc_entry_parser import MCCEntryParser


@pytest.fixture
def parser() -> MCCEntryParser:
    return MCCEntryParser()


class TestMCCEntryParserValid:
    def test_parse_valid_entry_all_fields(self, parser: MCCEntryParser) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Eating Places", "Restaurants and cafes serving food."],
            "_included_lines": ["Cafes", "Food Courts"],
            "_similar_lines": ["5814 – Fast Food Restaurants"],
        }
        entry = parser.parse(raw, source_image="page-27.jpg")

        assert entry.mcc == "5812"
        assert entry.title == "Eating Places"
        assert entry.description == "Restaurants and cafes serving food."
        assert entry.included_in_mcc == ["Cafes", "Food Courts"]
        assert entry.similar_merchants == [
            SimilarMerchant(mcc="5814", title="Fast Food Restaurants")
        ]
        assert entry.source_image == "page-27.jpg"
        assert entry.unparsed is False

    def test_single_desc_line_has_no_description(self, parser: MCCEntryParser) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Only Title"],
            "_included_lines": [],
            "_similar_lines": [],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert entry.title == "Only Title"
        assert entry.description is None

    def test_no_desc_lines_title_and_description_none(
        self, parser: MCCEntryParser
    ) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": [],
            "_included_lines": [],
            "_similar_lines": [],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert entry.title is None
        assert entry.description is None


class TestMCCEntryParserUnparsed:
    def test_empty_mcc_marks_unparsed(self, parser: MCCEntryParser) -> None:
        raw = {
            "mcc": "",
            "_desc_lines": ["Something"],
            "_included_lines": [],
            "_similar_lines": [],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert entry.unparsed is True
        assert entry.mcc == ""


class TestMCCEntryParserSimilarMerchants:
    def test_title_continuation_across_lines(self, parser: MCCEntryParser) -> None:
        """A line not matching MCC pattern appends to previous merchant's title."""
        raw = {
            "mcc": "0742",
            "_desc_lines": ["Veterinary Services"],
            "_included_lines": [],
            "_similar_lines": [
                "5995 – Pet Shops, Pet Foods and",
                "Supplies Store",
            ],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert len(entry.similar_merchants) == 1
        assert entry.similar_merchants[0].mcc == "5995"
        assert (
            entry.similar_merchants[0].title
            == "Pet Shops, Pet Foods and Supplies Store"
        )

    def test_multiple_merchants(self, parser: MCCEntryParser) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Eating Places"],
            "_included_lines": [],
            "_similar_lines": [
                "5813 – Drinking Places",
                "5814 – Fast Food Restaurants",
            ],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert len(entry.similar_merchants) == 2
        assert entry.similar_merchants[0].mcc == "5813"
        assert entry.similar_merchants[1].mcc == "5814"

    def test_en_dash_and_hyphen_both_supported(
        self, parser: MCCEntryParser
    ) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Eating Places"],
            "_included_lines": [],
            "_similar_lines": [
                "5813 – En Dash",
                "5814 - Hyphen",
            ],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert len(entry.similar_merchants) == 2
        assert entry.similar_merchants[0].title == "En Dash"
        assert entry.similar_merchants[1].title == "Hyphen"

    def test_continuation_without_pending_is_dropped(
        self, parser: MCCEntryParser
    ) -> None:
        """Lines that don't match and have no pending merchant are ignored (header)."""
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Eating Places"],
            "_included_lines": [],
            "_similar_lines": [
                "Similar Merchants Header",
                "5814 – Fast Food",
            ],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert len(entry.similar_merchants) == 1
        assert entry.similar_merchants[0].mcc == "5814"


class TestMCCEntryParserIncluded:
    def test_filter_short_lines(self, parser: MCCEntryParser) -> None:
        """Lines with <= 2 chars are filtered out."""
        raw = {
            "mcc": "5812",
            "_desc_lines": ["Eating"],
            "_included_lines": ["Cafes", "–", "ab", "Food Courts"],
            "_similar_lines": [],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert entry.included_in_mcc == ["Cafes", "Food Courts"]

    def test_empty_included_list(self, parser: MCCEntryParser) -> None:
        raw = {
            "mcc": "5812",
            "_desc_lines": ["A"],
            "_included_lines": [],
            "_similar_lines": [],
        }
        entry = parser.parse(raw, source_image="x.jpg")
        assert entry.included_in_mcc == []
