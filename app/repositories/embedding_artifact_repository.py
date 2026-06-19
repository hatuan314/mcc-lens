"""I/O repository for the embedding artifact (.npz).

Keeps NumPy/file concerns out of services. The producer writes a self-contained
``.npz``; the consumer reads it with a fail-fast validation checklist.
"""

import json
from pathlib import Path

import numpy as np

from app.models.embedding_artifact import EmbeddingArtifact

EXPECTED_DIM = 1024  # bge-m3

_REQUIRED_KEYS = (
    "mcc_vectors",
    "mcc_codes",
    "mcc_titles",
    "mcc_descriptions",
    "vsic_vectors",
    "vsic_codes",
    "vsic_titles",
    "meta",
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
            meta=np.array(json.dumps(artifact.meta), dtype=object),
        )

    def read(self, path: Path) -> EmbeddingArtifact:
        """Read and validate the artifact from ``path``.

        Validation is fail-fast, checked in order:
          1. file not found        -> FileNotFoundError
          2. not loadable / bad npz -> ValueError
          3. missing required key   -> ValueError (lists missing keys)
          4. wrong dimension        -> ValueError (vectors.shape[1] != 1024)
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
            raise ValueError(
                f"Embedding artifact missing required keys: {missing} (path: {path})"
            )

        mcc_vectors = data["mcc_vectors"]
        vsic_vectors = data["vsic_vectors"]

        # 4. wrong dimension
        for name, vectors in (("mcc", mcc_vectors), ("vsic", vsic_vectors)):
            if vectors.ndim != 2 or vectors.shape[1] != EXPECTED_DIM:
                raise ValueError(
                    f"Embedding artifact {name}_vectors has wrong dimension: "
                    f"expected (*, {EXPECTED_DIM}), got {vectors.shape}"
                )

        mcc_codes = list(data["mcc_codes"])
        mcc_titles = list(data["mcc_titles"])
        mcc_descriptions = list(data["mcc_descriptions"])
        vsic_codes = list(data["vsic_codes"])
        vsic_titles = list(data["vsic_titles"])

        # 5. length mismatch
        self._check_length("mcc_codes", mcc_codes, mcc_vectors)
        self._check_length("mcc_titles", mcc_titles, mcc_vectors)
        self._check_length("mcc_descriptions", mcc_descriptions, mcc_vectors)
        self._check_length("vsic_codes", vsic_codes, vsic_vectors)
        self._check_length("vsic_titles", vsic_titles, vsic_vectors)

        meta = json.loads(str(data["meta"]))

        return EmbeddingArtifact(
            mcc_vectors=mcc_vectors,
            mcc_codes=mcc_codes,
            mcc_titles=mcc_titles,
            mcc_descriptions=mcc_descriptions,
            vsic_vectors=vsic_vectors,
            vsic_codes=vsic_codes,
            vsic_titles=vsic_titles,
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
