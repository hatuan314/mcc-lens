"""Unit tests for EmbeddingArtifactRepository."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.models.embedding_artifact import EmbeddingArtifact
from app.repositories.embedding_artifact_repository import (
    EmbeddingArtifactRepository,
)

# Test fixture embedding dimension (dim is read dynamically from meta at runtime).
EXPECTED_DIM = 1024


def _artifact(n_mcc: int = 2, n_vsic: int = 3, dim: int = EXPECTED_DIM, rerank_top_n: int = 2) -> EmbeddingArtifact:
    return EmbeddingArtifact(
        mcc_vectors=np.ones((n_mcc, dim), dtype=np.float32),
        mcc_codes=[f"{1000 + i}" for i in range(n_mcc)],
        mcc_titles=[f"MCC {i}" for i in range(n_mcc)],
        mcc_descriptions=[f"desc {i}" for i in range(n_mcc)],
        vsic_vectors=np.ones((n_vsic, dim), dtype=np.float32),
        vsic_codes=[f"{i:04d}" for i in range(n_vsic)],
        vsic_titles=[f"VSIC {i}" for i in range(n_vsic)],
        reranked_mcc_indices=np.zeros((n_vsic, rerank_top_n), dtype=np.int32),
        rerank_scores=np.ones((n_vsic, rerank_top_n), dtype=np.float32) * 0.9,
        meta={
            "dim": dim,
            "zero_vector_codes": {"mcc": [], "vsic": []},
            "artifact_version": 2,
            "rerank_top_n": rerank_top_n,
        },
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
        assert loaded.reranked_mcc_indices.shape == (3, 2)
        assert np.allclose(loaded.rerank_scores, 0.9)

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
        # Thiếu reranked_mcc_indices và rerank_scores
        np.savez(
            path,
            mcc_vectors=np.ones((2, EXPECTED_DIM), dtype=np.float32),
            mcc_codes=np.array(["1000", "1001"], dtype=object),
            mcc_titles=np.array(["a", "b"], dtype=object),
            mcc_descriptions=np.array(["a", "b"], dtype=object),
            vsic_vectors=np.ones((1, EXPECTED_DIM), dtype=np.float32),
            vsic_codes=np.array(["0000"], dtype=object),
            vsic_titles=np.array(["x"], dtype=object),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM, "artifact_version": 2}), dtype=object),
        )
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="thiếu rerank"):
            repo.read(path)

    def test_old_version_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "old.npz"
        # meta.artifact_version != 2
        np.savez(
            path,
            mcc_vectors=np.ones((2, EXPECTED_DIM), dtype=np.float32),
            mcc_codes=np.array(["1000", "1001"], dtype=object),
            mcc_titles=np.array(["a", "b"], dtype=object),
            mcc_descriptions=np.array(["a", "b"], dtype=object),
            vsic_vectors=np.ones((1, EXPECTED_DIM), dtype=np.float32),
            vsic_codes=np.array(["0000"], dtype=object),
            vsic_titles=np.array(["x"], dtype=object),
            reranked_mcc_indices=np.zeros((1, 2), dtype=np.int32),
            rerank_scores=np.zeros((1, 2), dtype=np.float32),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM, "artifact_version": 1}), dtype=object),
        )
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="version cũ"):
            repo.read(path)

    def test_wrong_dimension_raises_value_error(self, tmp_path: Path) -> None:
        repo = EmbeddingArtifactRepository()
        path = tmp_path / "a.npz"
        repo.write(path, _artifact(dim=512))  # 512 != meta["dim"] trong meta (ở đây meta["dim"]=512 nhưng mcc_vectors có dim=512, tuy nhiên, check_dim sẽ fail nếu dim != EXPECTED_DIM? Khoan, repo check wrong dimension theo meta["dim"], nên để test wrong dimension, ta tạo vectors có dim=512 nhưng meta["dim"]=1024)
        
        path_wrong_dim = tmp_path / "wrong_dim.npz"
        np.savez(
            path_wrong_dim,
            mcc_vectors=np.ones((2, 512), dtype=np.float32),  # 512-dim
            mcc_codes=np.array(["1000", "1001"], dtype=object),
            mcc_titles=np.array(["a", "b"], dtype=object),
            mcc_descriptions=np.array(["a", "b"], dtype=object),
            vsic_vectors=np.ones((1, 512), dtype=np.float32),  # 512-dim
            vsic_codes=np.array(["0000"], dtype=object),
            vsic_titles=np.array(["x"], dtype=object),
            reranked_mcc_indices=np.zeros((1, 2), dtype=np.int32),
            rerank_scores=np.zeros((1, 2), dtype=np.float32),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM, "artifact_version": 2, "rerank_top_n": 2}), dtype=object),  # meta dim = 1024
        )
        with pytest.raises(ValueError, match="wrong dimension"):
            repo.read(path_wrong_dim)

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
            reranked_mcc_indices=np.zeros((1, 2), dtype=np.int32),
            rerank_scores=np.zeros((1, 2), dtype=np.float32),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM, "artifact_version": 2, "rerank_top_n": 2}), dtype=object),
        )
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="inconsistent"):
            repo.read(path)

    def test_rerank_shape_mismatch_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "rerank_mismatch.npz"
        np.savez(
            path,
            mcc_vectors=np.ones((2, EXPECTED_DIM), dtype=np.float32),
            mcc_codes=np.array(["1000", "1001"], dtype=object),
            mcc_titles=np.array(["a", "b"], dtype=object),
            mcc_descriptions=np.array(["a", "b"], dtype=object),
            vsic_vectors=np.ones((1, EXPECTED_DIM), dtype=np.float32),
            vsic_codes=np.array(["0000"], dtype=object),
            vsic_titles=np.array(["x"], dtype=object),
            reranked_mcc_indices=np.zeros((1, 5), dtype=np.int32),  # rerank_top_n = 5 but meta says 2
            rerank_scores=np.zeros((1, 5), dtype=np.float32),
            meta=np.array(json.dumps({"dim": EXPECTED_DIM, "artifact_version": 2, "rerank_top_n": 2}), dtype=object),
        )
        repo = EmbeddingArtifactRepository()
        with pytest.raises(ValueError, match="reranked_mcc_indices shape mismatch"):
            repo.read(path)
