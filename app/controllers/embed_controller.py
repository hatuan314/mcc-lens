"""Controller for the `embed` CLI command (Module 1 — producer).

Loads MCC + VSIC JSON, embeds every entry via Ollama `bge-m3` (batch_size=1 to
avoid the NaN/GPU-corruption issue), and writes one self-contained `.npz`
artifact consumed later by `map-vsic-mcc`. Designed to run on Colab/GPU.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from loguru import logger
from tqdm import tqdm

from app.models.embedding_artifact import EmbeddingArtifact
from app.repositories.embedding_artifact_repository import (
    EXPECTED_DIM,
    EmbeddingArtifactRepository,
)
from app.repositories.ollama_embedding_client import OllamaEmbeddingClient
from app.services.embed_text_builder import build_mcc_text, build_vsic_text
from app.services.protocols import EmbeddingClient


class EmbedController:
    """Orchestrates embedding of all MCC + VSIC entries into one artifact."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        embedding_model: str = "bge-m3",
    ) -> None:
        """Initialize with Ollama embedding configuration."""
        self.ollama_host = ollama_host
        self.embedding_model = embedding_model

    def execute(
        self,
        mcc_input: Path,
        vsic_input: Path,
        output: Path,
        gdrive_output_dir: Optional[Path] = None,
    ) -> int:
        """Run the embedding pipeline and write the artifact.

        Args:
            mcc_input: MCC JSON input path.
            vsic_input: VSIC JSON input path.
            output: Artifact ``.npz`` output path.
            gdrive_output_dir: If set, the artifact is written under this dir.

        Returns:
            Exit code (0 = success, 1 = file not found, 2 = Ollama error,
            3 = IO error).
        """
        try:
            if gdrive_output_dir:
                if str(gdrive_output_dir).startswith("/content/drive"):
                    if not Path("/content/drive/MyDrive").exists():
                        logger.warning(
                            "Path starts with /content/drive but Google Drive "
                            "does not appear to be mounted. Output will be local."
                        )
                gdrive_output_dir.mkdir(parents=True, exist_ok=True)
                output = gdrive_output_dir / "embed-artifact.npz"
                logger.info(f"Using Google Drive output directory: {gdrive_output_dir}")

            if not mcc_input.exists():
                logger.error(f"MCC input file not found: {mcc_input}")
                return 1
            if not vsic_input.exists():
                logger.error(f"VSIC input file not found: {vsic_input}")
                return 1

            with open(mcc_input, "r", encoding="utf-8") as f:
                mcc_entries = json.load(f).get("mcc_list", [])
            with open(vsic_input, "r", encoding="utf-8") as f:
                vsic_entries = json.load(f).get("vsic_list", [])

            logger.info(
                f"Loaded {len(mcc_entries)} MCC entries and "
                f"{len(vsic_entries)} VSIC entries"
            )

            client = OllamaEmbeddingClient(self.ollama_host, self.embedding_model)

            mcc_texts = [build_mcc_text(m) for m in mcc_entries]
            vsic_texts = [build_vsic_text(v) for v in vsic_entries]

            mcc_vectors, mcc_zero = self._embed_all(client, mcc_texts, "MCC")
            vsic_vectors, vsic_zero = self._embed_all(client, vsic_texts, "VSIC")

            mcc_codes = [m["mcc"] for m in mcc_entries]
            vsic_codes = [v["code"] for v in vsic_entries]

            zero_mcc_codes = [mcc_codes[i] for i in mcc_zero]
            zero_vsic_codes = [vsic_codes[i] for i in vsic_zero]
            if zero_mcc_codes or zero_vsic_codes:
                logger.warning(
                    f"Zero-vector embeddings: {len(zero_mcc_codes)} MCC "
                    f"{zero_mcc_codes}, {len(zero_vsic_codes)} VSIC "
                    f"{zero_vsic_codes}. They will rank low but are still written."
                )

            artifact = EmbeddingArtifact(
                mcc_vectors=mcc_vectors,
                mcc_codes=mcc_codes,
                mcc_titles=[m["title"] for m in mcc_entries],
                mcc_descriptions=[m.get("description") or "" for m in mcc_entries],
                vsic_vectors=vsic_vectors,
                vsic_codes=vsic_codes,
                vsic_titles=[v["title"] for v in vsic_entries],
                meta={
                    "dim": EXPECTED_DIM,
                    "zero_vector_codes": {
                        "mcc": zero_mcc_codes,
                        "vsic": zero_vsic_codes,
                    },
                    "embedding_model": self.embedding_model,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
            )

            EmbeddingArtifactRepository().write(output, artifact)
            logger.info(
                f"Wrote embedding artifact to {output} "
                f"(mcc {mcc_vectors.shape}, vsic {vsic_vectors.shape})"
            )
            return 0

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return 1
        except RuntimeError as e:
            logger.error(f"Ollama error: {e}")
            return 2
        except IOError as e:
            logger.error(f"IO error: {e}")
            return 3
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return 1

    def _embed_all(
        self, client: EmbeddingClient, texts: List[str], label: str
    ) -> Tuple[np.ndarray, List[int]]:
        """Embed every text one at a time (batch_size=1).

        On unrecoverable embed failure or NaN output, substitutes a zero vector
        and records the index.

        Returns:
            (matrix of shape ``(len(texts), EXPECTED_DIM)``, list of zero-vector
            indices).
        """
        vectors: List[List[float]] = []
        zero_indices: List[int] = []
        dim = EXPECTED_DIM
        with tqdm(total=len(texts), desc=f"Embedding {label}") as pbar:
            for i, text in enumerate(texts):
                try:
                    vec = client.embed([text])[0]
                    if not vec or any(np.isnan(vec)):
                        raise ValueError("empty or NaN embedding")
                    dim = len(vec)
                    vectors.append(list(vec))
                except (RuntimeError, ValueError) as e:
                    logger.warning(
                        f"{label} embedding failed at index {i} "
                        f"— using zero vector. Error: {e}"
                    )
                    vectors.append([0.0] * dim)
                    zero_indices.append(i)
                pbar.update(1)

        return np.array(vectors, dtype=np.float32), zero_indices
