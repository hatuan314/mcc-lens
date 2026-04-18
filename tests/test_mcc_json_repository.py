"""
Unit tests for MCCJsonRepository.
"""

import json
from pathlib import Path

import pytest

from app.models.mcc_entry import MCCEntry, SimilarMerchant
from app.repositories.mcc_json_repository import MCCJsonRepository


@pytest.fixture
def repo() -> MCCJsonRepository:
    return MCCJsonRepository()


def make_entry(mcc: str = "5812") -> MCCEntry:
    return MCCEntry(
        mcc=mcc,
        title="Eating Places",
        description="Restaurants",
        included_in_mcc=["Cafes"],
        similar_merchants=[SimilarMerchant(mcc="5814", title="Fast Food")],
        source_image="p1.jpg",
        unparsed=False,
    )


class TestMCCJsonRepository:
    def test_output_schema(self, repo: MCCJsonRepository, tmp_path: Path) -> None:
        output = tmp_path / "out.json"
        repo.save([make_entry("5812"), make_entry("5814")], output)

        data = json.loads(output.read_text(encoding="utf-8"))

        assert set(data.keys()) == {"source", "total_mcc_count", "mcc_list"}
        assert data["total_mcc_count"] == 2
        assert isinstance(data["mcc_list"], list)
        assert len(data["mcc_list"]) == 2

    def test_entry_has_six_fields(
        self, repo: MCCJsonRepository, tmp_path: Path
    ) -> None:
        output = tmp_path / "out.json"
        repo.save([make_entry()], output)

        data = json.loads(output.read_text(encoding="utf-8"))
        entry = data["mcc_list"][0]
        expected_keys = {
            "mcc",
            "title",
            "description",
            "included_in_mcc",
            "similar_merchants",
            "source_image",
            "_unparsed",
        }
        assert set(entry.keys()) == expected_keys
        # Legacy key must not leak into output
        assert "unparsed" not in entry

    def test_similar_merchants_serialized_as_dict(
        self, repo: MCCJsonRepository, tmp_path: Path
    ) -> None:
        output = tmp_path / "out.json"
        repo.save([make_entry()], output)

        data = json.loads(output.read_text(encoding="utf-8"))
        merchants = data["mcc_list"][0]["similar_merchants"]
        assert merchants == [{"mcc": "5814", "title": "Fast Food"}]

    def test_creates_parent_directory(
        self, repo: MCCJsonRepository, tmp_path: Path
    ) -> None:
        nested = tmp_path / "a" / "b" / "c" / "out.json"
        assert not nested.parent.exists()

        repo.save([make_entry()], nested)

        assert nested.exists()
        assert nested.parent.is_dir()

    def test_utf8_encoding(self, repo: MCCJsonRepository, tmp_path: Path) -> None:
        entry = MCCEntry(
            mcc="5812",
            title="Ăn uống – Nhà hàng",
            description="Mô tả tiếng Việt với dấu – en dash",
            included_in_mcc=["Café"],
            similar_merchants=[],
            source_image="p1.jpg",
        )
        output = tmp_path / "out.json"
        repo.save([entry], output)

        content = output.read_text(encoding="utf-8")
        assert "Ăn uống" in content
        assert "–" in content  # en dash preserved
        assert "\\u" not in content  # no ascii escaping

    def test_empty_list(self, repo: MCCJsonRepository, tmp_path: Path) -> None:
        output = tmp_path / "out.json"
        repo.save([], output)

        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["total_mcc_count"] == 0
        assert data["mcc_list"] == []
