"""Unit tests for EmbedController (Module 1 — producer)."""

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app.controllers.embed_controller import EmbedController
from app.repositories.embedding_artifact_repository import (
    EXPECTED_DIM,
    EmbeddingArtifactRepository,
)


def _write_mcc_json(path: Path, n: int = 2) -> None:
    path.write_text(
        json.dumps(
            {
                "mcc_list": [
                    {"mcc": f"{1000 + i}", "title": f"MCC {i}", "description": "d"}
                    for i in range(n)
                ]
            }
        ),
        encoding="utf-8",
    )


def _write_vsic_json(path: Path, n: int = 3) -> None:
    path.write_text(
        json.dumps(
            {"vsic_list": [{"code": f"{i:04d}", "title": f"VSIC {i}"} for i in range(n)]}
        ),
        encoding="utf-8",
    )


class _FakeEmbeddingClient:
    """Returns a 1024-dim unit vector for each text."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def embed(self, texts):
        return [[1.0] + [0.0] * (EXPECTED_DIM - 1) for _ in texts]


class _ZeroForOneClient:
    """Raises for a specific text to force a zero vector."""

    def __init__(self, fail_text: str) -> None:
        self.fail_text = fail_text

    def __call__(self, *args, **kwargs):
        return self

    def embed(self, texts):
        if texts[0] == self.fail_text:
            raise RuntimeError("simulated NaN failure")
        return [[1.0] + [0.0] * (EXPECTED_DIM - 1) for _ in texts]


class TestEmbedControllerHappyPath:
    def test_produces_artifact_with_correct_shapes(self, tmp_path: Path) -> None:
        mcc = tmp_path / "mcc.json"
        vsic = tmp_path / "vsic.json"
        out = tmp_path / "art.npz"
        _write_mcc_json(mcc, n=2)
        _write_vsic_json(vsic, n=3)

        with patch(
            "app.controllers.embed_controller.OllamaEmbeddingClient",
            _FakeEmbeddingClient,
        ):
            code = EmbedController().execute(mcc_input=mcc, vsic_input=vsic, output=out)

        assert code == 0
        artifact = EmbeddingArtifactRepository().read(out)
        assert artifact.mcc_vectors.shape == (2, EXPECTED_DIM)
        assert artifact.vsic_vectors.shape == (3, EXPECTED_DIM)
        assert artifact.mcc_codes == ["1000", "1001"]
        assert artifact.meta["dim"] == EXPECTED_DIM

    def test_returns_1_when_input_missing(self, tmp_path: Path) -> None:
        vsic = tmp_path / "vsic.json"
        _write_vsic_json(vsic)
        code = EmbedController().execute(
            mcc_input=tmp_path / "missing.json",
            vsic_input=vsic,
            output=tmp_path / "art.npz",
        )
        assert code == 1


class TestEmbedControllerZeroVector:
    def test_zero_vector_recorded_in_meta(self, tmp_path: Path) -> None:
        mcc = tmp_path / "mcc.json"
        vsic = tmp_path / "vsic.json"
        out = tmp_path / "art.npz"
        _write_mcc_json(mcc, n=2)  # codes 1000, 1001; titles "MCC 0/1"
        _write_vsic_json(vsic, n=1)

        # Fail the second MCC text ("MCC 1 — d") → its code 1001 becomes zero.
        fake = _ZeroForOneClient(fail_text="MCC 1 — d")
        with patch(
            "app.controllers.embed_controller.OllamaEmbeddingClient", fake
        ):
            code = EmbedController().execute(mcc_input=mcc, vsic_input=vsic, output=out)

        assert code == 0
        artifact = EmbeddingArtifactRepository().read(out)
        assert artifact.meta["zero_vector_codes"]["mcc"] == ["1001"]
        # The zero-vector row is all zeros.
        assert np.allclose(artifact.mcc_vectors[1], 0.0)
        assert not np.allclose(artifact.mcc_vectors[0], 0.0)
