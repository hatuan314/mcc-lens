"""
Unit tests for VsicJsonRepository.
"""

import json
from pathlib import Path

import pytest

from app.models.vsic_entry import VsicEntry
from app.repositories.vsic_json_repository import VsicJsonRepository


@pytest.fixture
def repo() -> VsicJsonRepository:
    return VsicJsonRepository()


@pytest.fixture
def sample_entries() -> list:
    return [
        VsicEntry(code="1110", title="Trồng lúa", digits=4),
        VsicEntry(code="11100", title="Trồng lúa chi tiết", digits=5),
    ]


class TestVsicJsonRepository:
    def test_creates_output_file(
        self, repo: VsicJsonRepository, tmp_path: Path, sample_entries: list
    ) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries(sample_entries, out)
        assert out.exists()

    def test_output_is_flat_array(
        self, repo: VsicJsonRepository, tmp_path: Path, sample_entries: list
    ) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries(sample_entries, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_entry_count(
        self, repo: VsicJsonRepository, tmp_path: Path, sample_entries: list
    ) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries(sample_entries, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_entry_schema(
        self, repo: VsicJsonRepository, tmp_path: Path, sample_entries: list
    ) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries(sample_entries, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        first = data[0]
        assert first["code"] == "1110"
        assert first["title"] == "Trồng lúa"
        assert first["digits"] == 4

    def test_no_extra_fields(
        self, repo: VsicJsonRepository, tmp_path: Path, sample_entries: list
    ) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries(sample_entries, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data[0].keys()) == {"code", "title", "digits"}

    def test_creates_parent_dirs(
        self, repo: VsicJsonRepository, tmp_path: Path
    ) -> None:
        out = tmp_path / "nested" / "dir" / "vsic.json"
        repo.write_entries([], out)
        assert out.exists()

    def test_empty_list(self, repo: VsicJsonRepository, tmp_path: Path) -> None:
        out = tmp_path / "vsic.json"
        repo.write_entries([], out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data == []

    def test_unicode_preserved(self, repo: VsicJsonRepository, tmp_path: Path) -> None:
        entries = [VsicEntry(code="1110", title="Trồng lúa tiếng Việt", digits=4)]
        out = tmp_path / "vsic.json"
        repo.write_entries(entries, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["title"] == "Trồng lúa tiếng Việt"
