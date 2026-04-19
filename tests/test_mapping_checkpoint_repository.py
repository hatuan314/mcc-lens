"""Unit tests for MappingCheckpointRepository."""

from pathlib import Path


from app.repositories.mapping_checkpoint_repository import MappingCheckpointRepository


def _make_repo(tmp_path: Path) -> MappingCheckpointRepository:
    return MappingCheckpointRepository(tmp_path / ".mapping-progress.json")


class TestLoad:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        assert repo.load() == {}

    def test_load_returns_saved_data(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"top_results": [{"mcc_code": "5411"}]})
        data = repo.load()
        assert "1110" in data
        assert data["1110"]["top_results"][0]["mcc_code"] == "5411"

    def test_load_handles_corrupted_file(self, tmp_path: Path) -> None:
        path = tmp_path / ".mapping-progress.json"
        path.write_text("not valid json", encoding="utf-8")
        repo = MappingCheckpointRepository(path)
        assert repo.load() == {}


class TestSave:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"top_results": []})
        assert (tmp_path / ".mapping-progress.json").exists()

    def test_save_multiple_entries_accumulates(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"top_results": []})
        repo.save("1120", {"top_results": []})
        data = repo.load()
        assert "1110" in data
        assert "1120" in data

    def test_save_is_atomic_no_tmp_file_left(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"top_results": []})
        tmp_file = tmp_path / ".mapping-progress.tmp"
        assert not tmp_file.exists()

    def test_save_overwrites_existing_entry(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"top_results": [{"mcc_code": "5411"}]})
        repo.save("1110", {"top_results": [{"mcc_code": "7372"}]})
        data = repo.load()
        assert data["1110"]["top_results"][0]["mcc_code"] == "7372"

    def test_save_preserves_unicode(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        repo.save("1110", {"vsic_title": "Trồng lúa", "top_results": []})
        data = repo.load()
        assert data["1110"]["vsic_title"] == "Trồng lúa"
