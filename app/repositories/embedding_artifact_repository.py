"""I/O repository for the embedding artifact (.npz).

Keeps NumPy/file concerns out of services. The producer writes a self-contained
``.npz``; the consumer reads it with a fail-fast validation checklist.
"""

import json
from pathlib import Path

import numpy as np

from app.models.embedding_artifact import EmbeddingArtifact

_REQUIRED_KEYS = (
    "mcc_vectors",
    "mcc_codes",
    "mcc_titles",
    "mcc_descriptions",
    "vsic_vectors",
    "vsic_codes",
    "vsic_titles",
    "meta",
    "reranked_mcc_indices",
    "rerank_scores",
)


class EmbeddingArtifactRepository:
    """Read/write the embedding artifact ``.npz`` file."""

    def write(self, path: Path, artifact: EmbeddingArtifact) -> None:
        """Write the artifact to ``path`` via ``np.savez``.

        Args:
            path: Destination ``.npz`` path. Parent dirs are created.
            artifact: The artifact to persist.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            mcc_vectors=np.asarray(artifact.mcc_vectors, dtype=np.float32),
            mcc_codes=np.array(artifact.mcc_codes, dtype=object),
            mcc_titles=np.array(artifact.mcc_titles, dtype=object),
            mcc_descriptions=np.array(artifact.mcc_descriptions, dtype=object),
            vsic_vectors=np.asarray(artifact.vsic_vectors, dtype=np.float32),
            vsic_codes=np.array(artifact.vsic_codes, dtype=object),
            vsic_titles=np.array(artifact.vsic_titles, dtype=object),
            reranked_mcc_indices=np.asarray(artifact.reranked_mcc_indices, dtype=np.int32),
            rerank_scores=np.asarray(artifact.rerank_scores, dtype=np.float32),
            meta=np.array(json.dumps(artifact.meta), dtype=object),
        )

    def read(self, path: Path) -> EmbeddingArtifact:
        """Read and validate the artifact from ``path``.

        Validation is fail-fast, checked in order:
          1. file not found        -> FileNotFoundError
          2. not loadable / bad npz -> ValueError
          3. missing required key   -> ValueError (lists missing keys)
          4. wrong dimension        -> ValueError (vectors.shape[1] != dim)
          5. length mismatch        -> ValueError (len(codes) != vectors rows)

        Args:
            path: Path to the artifact ``.npz``.

        Returns:
            The loaded EmbeddingArtifact.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: On corrupt file, missing key, wrong dim, or length mismatch.
        """
        path = Path(path)
        # 1. file not found
        if not path.exists():
            raise FileNotFoundError(
                f"Embedding artifact not found at '{path}'. "
                "Run `python3 main.py embed` on Colab first."
            )

        # 2. not loadable / bad npz
        try:
            data = np.load(path, allow_pickle=True)
        except Exception as e:
            raise ValueError(
                f"Embedding artifact corrupt or not a valid .npz: {path} ({e})"
            ) from e

        # 3. missing required key
        missing = [k for k in _REQUIRED_KEYS if k not in data.files]
        if missing:
            if "reranked_mcc_indices" in missing or "rerank_scores" in missing:
                raise ValueError(
                    "artifact thiếu rerank — regenerate bằng `python3 main.py embed`"
                )
            raise ValueError(
                f"Embedding artifact missing required keys: {missing} (path: {path})"
            )

        meta = json.loads(str(data["meta"]))

        # Validate artifact version
        if meta.get("artifact_version") != 2:
            raise ValueError("artifact version cũ — regenerate")

        dim = meta.get("dim")
        if not dim:
            raise ValueError("artifact thiếu thông tin dim trong meta — regenerate")

        mcc_vectors = data["mcc_vectors"]
        vsic_vectors = data["vsic_vectors"]

        # 4. wrong dimension
        for name, vectors in (("mcc", mcc_vectors), ("vsic", vsic_vectors)):
            if vectors.ndim != 2 or vectors.shape[1] != dim:
                raise ValueError(
                    f"Embedding artifact {name}_vectors has wrong dimension: "
                    f"expected (*, {dim}), got {vectors.shape}"
                )

        mcc_codes = list(data["mcc_codes"])
        mcc_titles = list(data["mcc_titles"])
        mcc_descriptions = list(data["mcc_descriptions"])
        vsic_codes = list(data["vsic_codes"])
        vsic_titles = list(data["vsic_titles"])
        
        reranked_mcc_indices = data["reranked_mcc_indices"]
        rerank_scores = data["rerank_scores"]

        # Validate rerank shapes
        n_vsic = len(vsic_codes)
        rerank_top_n = meta.get("rerank_top_n")
        if rerank_top_n is None:
            raise ValueError("artifact thiếu rerank_top_n trong meta")

        if reranked_mcc_indices.shape != (n_vsic, rerank_top_n):
            raise ValueError(
                f"reranked_mcc_indices shape mismatch: "
                f"expected ({n_vsic}, {rerank_top_n}), got {reranked_mcc_indices.shape}"
            )
        if rerank_scores.shape != reranked_mcc_indices.shape:
            raise ValueError(
                f"rerank_scores shape mismatch: "
                f"expected {reranked_mcc_indices.shape}, got {rerank_scores.shape}"
            )

        # 5. length mismatch
        self._check_length("mcc_codes", mcc_codes, mcc_vectors)
        self._check_length("mcc_titles", mcc_titles, mcc_vectors)
        self._check_length("mcc_descriptions", mcc_descriptions, mcc_vectors)
        self._check_length("vsic_codes", vsic_codes, vsic_vectors)
        self._check_length("vsic_titles", vsic_titles, vsic_vectors)

        return EmbeddingArtifact(
            mcc_vectors=mcc_vectors,
            mcc_codes=mcc_codes,
            mcc_titles=mcc_titles,
            mcc_descriptions=mcc_descriptions,
            vsic_vectors=vsic_vectors,
            vsic_codes=vsic_codes,
            vsic_titles=vsic_titles,
            reranked_mcc_indices=reranked_mcc_indices,
            rerank_scores=rerank_scores,
            meta=meta,
        )

    @staticmethod
    def _check_length(name: str, values: list, vectors: np.ndarray) -> None:
        """Raise if ``values`` length does not match the number of vector rows."""
        if len(values) != vectors.shape[0]:
            raise ValueError(
                f"Embedding artifact inconsistent: {len(values)} {name} "
                f"vs {vectors.shape[0]} vectors"
            )
