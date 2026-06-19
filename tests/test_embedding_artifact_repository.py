"""Unit tests for EmbeddingArtifactRepository."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.models.embedding_artifact import EmbeddingArtifact
from app.repositories.embedding_artifact_repository import (
    EXPECTED_DIM,
    EmbeddingArtifactRepository,
)


def _artifact(n_mcc: int = 2, n_vsic: int = 3, dim: int = EXPECTED_DIM) -> EmbeddingArtifact:
    return EmbeddingArtifact(
        mcc_vectors=np.ones((n_mcc, dim), dtype=np.float32),
        mcc_codes=[f"{1000 + i}" for i in range(n_mcc)],
        mcc_titles=[f"MCC {i}" for i in range(n_mcc)],
        mcc_descriptions=[f"desc {i}" for i in range(n_mcc)],
        vsic_vectors=np.ones((n_vsic, dim), dtype=np.float32),
        vsic_codes=[f"{i:04d}" for i in range(n_vsic)],
        vsic_titles=[f"VSIC {i}" for i in range(n_vsic)],
        meta={"dim": dim, "zero_vector_codes": {"mcc": [], "vsic": []}},
    )


class TestRoundTrip:
    def test_write_then_read_preserves_data(self, tmp_path: Path) -> None:
        repo = EmbeddingArtifactRepository()
        path = tmp_path / "a.npz"
        repo.write(path, _artifact())
        loaded = repo.read(path)

        assert loaded.mcc_vectors.shape == (2, EXPECTED_DIM)
        assert loaded.vsic_vectors.shape == (3, EXPECTED_DIM)
        assert loaded.mcc_codes == ["1000", "1001"]
        assert loaded.vsic_titles == ["VSIC 0", "VSIC 1", "VSIC 2"]
        assert loaded.meta["dim"] == EXPECTED_DIM

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        repo = EmbeddingArtifactRepository()
        path = tmp_path / "nested" / "deep" / "a.npz"
        repo.write(path, _artifact())
        assert path.exists()


class TestHardFail:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        repo = EmbeddingArtifactRepository()
        with pytest.raises(FileNotFoundError):
            repo.read(tmp_path / "missing.npz")

    def test_corrupt_file_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.npz"
        path.write_text("not an npz")
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError):
            repo.read(path)

    def test_missing_key_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.npz"
        np.savez(path, mcc_vectors=np.ones((2, EXPECTED_DIM), dtype=np.float32))
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="missing required keys"):
            repo.read(path)

    def test_wrong_dimension_raises_value_error(self, tmp_path: Path) -> None:
        repo = EmbeddingArtifactRepository()
        path = tmp_path / "a.npz"
        repo.write(path, _artifact(dim=512))  # 512 != 1024
        with pytest.raises(ValueError, match="wrong dimension"):
            repo.read(path)

    def test_length_mismatch_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "mismatch.npz"
        np.savez(
            path,
            mcc_vectors=np.ones((2, EXPECTED_DIM), dtype=np.float32),
            mcc_codes=np.array(["1000"], dtype=object),  # 1 code vs 2 vectors
            mcc_titles=np.array(["a", "b"], dtype=object),
            mcc_descriptions=np.array(["a", "b"], dtype=object),
            vsic_vectors=np.ones((1, EXPECTED_DIM), dtype=np.float32),
            vsic_codes=np.array(["0000"], dtype=object),
            vsic_titles=np.array(["x"], dtype=object),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM}), dtype=object),
        )
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="inconsistent"):
            repo.read(path)
