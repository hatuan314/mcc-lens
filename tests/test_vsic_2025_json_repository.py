"""
Unit tests for VSIC 2025 JSON Repository.
"""

import json
from pathlib import Path

import pytest

from app.models.vsic_2025_entry import Vsic2025Entry, VsicLevel5Child
from app.repositories.vsic_2025_json_repository import Vsic2025JsonRepository


@pytest.fixture
def repository() -> Vsic2025JsonRepository:
    return Vsic2025JsonRepository()


@pytest.fixture
def sample_entries() -> list[Vsic2025Entry]:
    return [
        Vsic2025Entry(
            code="111",
            title="Trồng lúa",
            children_level5=[
                VsicLevel5Child(code="1110", title="Lúa hạt"),
                VsicLevel5Child(code="1111", title="Lúa gạo"),
            ],
        ),
        Vsic2025Entry(
            code="112",
            title="Trồng ngô",
            children_level5=[],
        ),
    ]


class TestWriteEntries:
    """Tests for write_entries method."""

    def test_creates_output_file(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        assert output_file.exists()

    def test_creates_parent_directories(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "nested" / "dir" / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        assert output_file.exists()

    def test_output_has_source_field(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(
            sample_entries, output_file, source="assets/vsic-vn/vsic-2025.xlsx"
        )

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["source"] == "assets/vsic-vn/vsic-2025.xlsx"

    def test_output_has_total_vsic_count(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_vsic_count"] == 2

    def test_output_has_vsic_list(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "vsic_list" in data
        assert len(data["vsic_list"]) == 2

    def test_entry_has_code_title_children(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entry = data["vsic_list"][0]
        assert entry["code"] == "111"
        assert entry["title"] == "Trồng lúa"
        assert "children_level5" in entry

    def test_children_structure(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        children = data["vsic_list"][0]["children_level5"]
        assert len(children) == 2
        assert children[0]["code"] == "1110"
        assert children[0]["title"] == "Lúa hạt"
        assert children[1]["code"] == "1111"

    def test_entry_without_children(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entry = data["vsic_list"][1]
        assert entry["code"] == "112"
        assert entry["children_level5"] == []

    def test_empty_entries_list(
        self,
        repository: Vsic2025JsonRepository,
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries([], output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_vsic_count"] == 0
        assert data["vsic_list"] == []

    def test_json_is_pretty_printed(
        self,
        repository: Vsic2025JsonRepository,
        sample_entries: list[Vsic2025Entry],
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "output.json"

        repository.write_entries(sample_entries, output_file, source="test.xlsx")

        content = output_file.read_text(encoding="utf-8")
        # Pretty printed JSON should have newlines and indentation
        assert "\n" in content
        assert "  " in content

    def test_vietnamese_characters_preserved(
        self,
        repository: Vsic2025JsonRepository,
        tmp_path: Path,
    ) -> None:
        entries = [
            Vsic2025Entry(
                code="111",
                title="Trồng lúa nước",
                children_level5=[VsicLevel5Child(code="1110", title="Lúa gạo Việt")],
            )
        ]
        output_file = tmp_path / "output.json"

        repository.write_entries(entries, output_file, source="test.xlsx")

        content = output_file.read_text(encoding="utf-8")
        assert "Trồng lúa nước" in content
        assert "Lúa gạo Việt" in content


class TestOutputSchemaCompliance:
    """Tests verifying output matches required schema."""

    def test_no_extra_fields_in_entry(
        self,
        repository: Vsic2025JsonRepository,
        tmp_path: Path,
    ) -> None:
        entries = [Vsic2025Entry(code="111", title="Test", children_level5=[])]
        output_file = tmp_path / "output.json"

        repository.write_entries(entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entry = data["vsic_list"][0]
        assert set(entry.keys()) == {"code", "title", "children_level5"}

    def test_no_extra_fields_in_child(
        self,
        repository: Vsic2025JsonRepository,
        tmp_path: Path,
    ) -> None:
        entries = [
            Vsic2025Entry(
                code="111",
                title="Test",
                children_level5=[VsicLevel5Child(code="1110", title="Child")],
            )
        ]
        output_file = tmp_path / "output.json"

        repository.write_entries(entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        child = data["vsic_list"][0]["children_level5"][0]
        assert set(child.keys()) == {"code", "title"}

    def test_root_level_fields(
        self,
        repository: Vsic2025JsonRepository,
        tmp_path: Path,
    ) -> None:
        entries = [Vsic2025Entry(code="111", title="Test", children_level5=[])]
        output_file = tmp_path / "output.json"

        repository.write_entries(entries, output_file, source="test.xlsx")

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert set(data.keys()) == {"source", "total_vsic_count", "vsic_list"}
