"""
Unit tests for EntryGrouper.
"""

import pytest

from app.models.ocr_line import OCRLine
from app.services.entry_grouper import EntryGrouper


@pytest.fixture
def grouper() -> EntryGrouper:
    return EntryGrouper()


def line(text: str, x1: float = 0.0, y1: float = 0.0) -> OCRLine:
    return OCRLine(text=text, bbox=[x1, y1, x1 + 10.0, y1 + 20.0], confidence=1.0)


class TestEntryGrouperSingleEntry:
    def test_single_entry_with_all_columns(self, grouper: EntryGrouper) -> None:
        classified = [
            (line("5812"), "mcc"),
            (line("Eating Places"), "desc"),
            (line("Restaurants"), "desc"),
            (line("Restaurants"), "included"),
            (line("5814 – Fast Food"), "similar"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 1
        e = entries[0]
        assert e["mcc"] == "5812"
        assert e["_desc_lines"] == ["Eating Places", "Restaurants"]
        assert e["_included_lines"] == ["Restaurants"]
        assert e["_similar_lines"] == ["5814 – Fast Food"]


class TestEntryGrouperMultipleEntries:
    def test_multiple_entries_split_on_mcc_code(self, grouper: EntryGrouper) -> None:
        classified = [
            (line("5812"), "mcc"),
            (line("Eating Places"), "desc"),
            (line("5814"), "mcc"),
            (line("Fast Food"), "desc"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 2
        assert entries[0]["mcc"] == "5812"
        assert entries[0]["_desc_lines"] == ["Eating Places"]
        assert entries[1]["mcc"] == "5814"
        assert entries[1]["_desc_lines"] == ["Fast Food"]

    def test_last_entry_is_not_lost(self, grouper: EntryGrouper) -> None:
        classified = [
            (line("5812"), "mcc"),
            (line("A"), "desc"),
            (line("5814"), "mcc"),
            (line("B"), "desc"),
            (line("5999"), "mcc"),
            (line("Last"), "desc"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 3
        assert entries[-1]["mcc"] == "5999"
        assert entries[-1]["_desc_lines"] == ["Last"]


class TestEntryGrouperSkipBeforeFirstMCC:
    def test_lines_before_first_mcc_are_ignored(self, grouper: EntryGrouper) -> None:
        classified = [
            (line("Header Title"), "desc"),  # before any MCC code
            (line("Another header"), "included"),  # before any MCC code
            (line("5812"), "mcc"),
            (line("Eating Places"), "desc"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 1
        assert entries[0]["mcc"] == "5812"
        assert entries[0]["_desc_lines"] == ["Eating Places"]

    def test_empty_input_returns_empty(self, grouper: EntryGrouper) -> None:
        assert grouper.group([]) == []

    def test_non_mcc_code_in_mcc_column_ignored(self, grouper: EntryGrouper) -> None:
        """A line in mcc column that doesn't match ^\\d{4}$ does NOT trigger a new entry."""
        classified = [
            (line("5812"), "mcc"),
            (line("Eating Places"), "desc"),
            (line("not-a-code"), "mcc"),  # ignored — not 4 digits
            (line("More desc"), "desc"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 1
        assert entries[0]["mcc"] == "5812"
        assert entries[0]["_desc_lines"] == ["Eating Places", "More desc"]


class TestEntryGrouperUnknownColumn:
    def test_unknown_column_is_dropped(self, grouper: EntryGrouper) -> None:
        classified = [
            (line("5812"), "mcc"),
            (line("Eating Places"), "desc"),
            (line("garbage"), "unknown"),
        ]
        entries = grouper.group(classified)

        assert len(entries) == 1
        assert entries[0]["_desc_lines"] == ["Eating Places"]
        assert entries[0]["_included_lines"] == []
        assert entries[0]["_similar_lines"] == []
