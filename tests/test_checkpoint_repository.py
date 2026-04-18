"""
Unit tests for CheckpointRepository.

Covers: load (missing file, valid file, invalid JSON), mark_done, clear, _persist,
OSError handlers in clear() and _persist().
"""

import json
import unicodedata
from pathlib import Path
from unittest.mock import patch

import pytest

from app.repositories.checkpoint_repository import CheckpointRepository


class TestCheckpointRepositoryLoad:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        repo = CheckpointRepository(tmp_path / "ckpt.json")
        result = repo.load()
        assert result == set()

    def test_load_returns_nfc_normalized_names(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        nfd_name = unicodedata.normalize("NFD", "hình ảnh-01.jpg")
        ckpt.write_text(json.dumps([nfd_name]), encoding="utf-8")

        repo = CheckpointRepository(ckpt)
        result = repo.load()

        expected_nfc = unicodedata.normalize("NFC", nfd_name)
        assert expected_nfc in result

    def test_load_ignores_non_string_entries(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        ckpt.write_text(json.dumps(["valid.jpg", 42, None, "other.jpg"]), encoding="utf-8")

        repo = CheckpointRepository(ckpt)
        result = repo.load()

        assert result == {"valid.jpg", "other.jpg"}

    def test_load_handles_invalid_json_gracefully(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        ckpt.write_text("not valid json", encoding="utf-8")

        repo = CheckpointRepository(ckpt)
        result = repo.load()
        assert result == set()

    def test_load_handles_non_list_json(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        ckpt.write_text(json.dumps({"key": "value"}), encoding="utf-8")

        repo = CheckpointRepository(ckpt)
        result = repo.load()
        assert result == set()


class TestCheckpointRepositoryMarkDone:
    def test_mark_done_persists_to_file(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        repo.mark_done("image.jpg")

        assert ckpt.exists()
        data = json.loads(ckpt.read_text(encoding="utf-8"))
        assert "image.jpg" in data

    def test_mark_done_accumulates_multiple_files(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        repo.mark_done("a.jpg")
        repo.mark_done("b.jpg")

        data = json.loads(ckpt.read_text(encoding="utf-8"))
        assert set(data) == {"a.jpg", "b.jpg"}

    def test_mark_done_normalizes_nfc(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        nfd_name = unicodedata.normalize("NFD", "hình ảnh-01.jpg")
        repo.mark_done(nfd_name)

        data = json.loads(ckpt.read_text(encoding="utf-8"))
        nfc_name = unicodedata.normalize("NFC", nfd_name)
        assert nfc_name in data

    def test_mark_done_creates_parent_directory(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "subdir" / "deep" / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        repo.mark_done("image.jpg")

        assert ckpt.exists()


class TestCheckpointRepositoryClear:
    def test_clear_deletes_checkpoint_file(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        ckpt.write_text(json.dumps(["a.jpg"]), encoding="utf-8")

        repo = CheckpointRepository(ckpt)
        repo.load()
        repo.clear()

        assert not ckpt.exists()

    def test_clear_when_file_missing_does_not_raise(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        repo.clear()  # should not raise

    def test_clear_empties_internal_state(self, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)
        repo.mark_done("a.jpg")

        repo.clear()

        assert repo.load() == set()

    def test_clear_oserror_does_not_raise(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = OSError("unlink failed")
        repo.checkpoint_path = mock_path

        repo.clear()  # should log warning and not raise


class TestCheckpointRepositoryPersistError:
    def test_persist_oserror_does_not_raise(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        ckpt = tmp_path / "ckpt.json"
        repo = CheckpointRepository(ckpt)

        mock_path = MagicMock(spec=Path)
        mock_path.parent.mkdir.return_value = None
        mock_path.write_text.side_effect = OSError("write failed")
        repo.checkpoint_path = mock_path

        repo.mark_done("a.jpg")  # should log warning and not raise
