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
from app.repositories.embedding_artifact_repository import EmbeddingArtifactRepository
from app.repositories.qwen3_embedding_client import Qwen3EmbeddingClient
from app.repositories.qwen3_reranker_client import Qwen3RerankerClient
from app.services.embed_text_builder import build_mcc_text, build_vsic_query
from app.services.protocols import EmbeddingClient


class EmbedController:
    """Orchestrates embedding of all MCC + VSIC entries into one artifact."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        embedding_model: str = "bge-m3",
        reranker_model: Optional[str] = None,
        rerank_top_n: int = 20,
        cosine_top_k: int = 100,
    ) -> None:
        """Initialize with embedding and reranker configuration."""
        self.ollama_host = ollama_host
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.rerank_top_n = rerank_top_n
        self.cosine_top_k = cosine_top_k

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
            Exit code (0 = success, 1 = file not found, 2 = Ollama/Model error,
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

            # Choose embedding client
            if self.embedding_model.startswith("Qwen"):
                client = Qwen3EmbeddingClient(self.embedding_model)
            else:
                from app.repositories.ollama_embedding_client import OllamaEmbeddingClient
                client = OllamaEmbeddingClient(self.ollama_host, self.embedding_model)

            mcc_texts = [build_mcc_text(m) for m in mcc_entries]
            # Use build_vsic_query for Qwen embedding client (needs instruction prefix)
            if self.embedding_model.startswith("Qwen"):
                vsic_texts = [build_vsic_query(v) for v in vsic_entries]
            else:
                from app.services.embed_text_builder import build_vsic_text
                vsic_texts = [build_vsic_text(v) for v in vsic_entries]

            mcc_vectors, mcc_zero = self._embed_all(client, mcc_texts, "MCC")
            vsic_vectors, vsic_zero = self._embed_all(client, vsic_texts, "VSIC")

            dim = mcc_vectors.shape[1]

            # Unload embedding client model to free GPU VRAM before loading reranker
            if hasattr(client, "_model"):
                logger.info("Unloading embedding model to free VRAM...")
                del client._model
                client._model = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            n_vsic = len(vsic_entries)
            reranked_mcc_indices = np.zeros((n_vsic, self.rerank_top_n), dtype=np.int32)
            rerank_scores = np.zeros((n_vsic, self.rerank_top_n), dtype=np.float32)

            mcc_norms = np.linalg.norm(mcc_vectors, axis=1)
            mcc_norms[mcc_norms == 0] = 1.0

            # Rerank phase
            if self.reranker_model:
                logger.info(f"Starting Qwen3-Reranker phase (cosine top-{self.cosine_top_k} -> rerank top-{self.rerank_top_n})")
                reranker = Qwen3RerankerClient(self.reranker_model)

                for i, vsic in enumerate(tqdm(vsic_entries, desc="Reranking VSIC")):
                    vsic_vec = vsic_vectors[i]
                    vsic_norm = np.linalg.norm(vsic_vec)
                    if vsic_norm == 0:
                        vsic_norm = 1.0

                    # Compute cosine similarities
                    sims = mcc_vectors @ vsic_vec / (mcc_norms * vsic_norm)
                    
                    # Get indices of top-K cosine matches
                    top_k_idxs = np.argsort(sims)[-self.cosine_top_k:][::-1]
                    
                    # Rerank these candidates
                    docs = [mcc_texts[idx] for idx in top_k_idxs]
                    query = vsic_texts[i]
                    
                    scores = reranker.rerank(query, docs)
                    
                    # Sort by score descending and take top-N
                    sorted_pairs = sorted(zip(scores, top_k_idxs), reverse=True)[:self.rerank_top_n]
                    
                    for k in range(self.rerank_top_n):
                        if k < len(sorted_pairs):
                            reranked_mcc_indices[i, k] = sorted_pairs[k][1]
                            rerank_scores[i, k] = sorted_pairs[k][0]
                        else:
                            # Fallback / Padding in case we got fewer candidates
                            reranked_mcc_indices[i, k] = -1
                            rerank_scores[i, k] = 0.0

                # Unload reranker to free GPU VRAM
                if hasattr(reranker, "_model"):
                    logger.info("Unloading reranker model to free VRAM...")
                    del reranker._model
                    reranker._model = None
                gc.collect()
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
            else:
                logger.info("No reranker model provided. Generating dummy rerank from cosine similarity for compatibility.")
                for i in range(n_vsic):
                    vsic_vec = vsic_vectors[i]
                    vsic_norm = np.linalg.norm(vsic_vec)
                    if vsic_norm == 0:
                        vsic_norm = 1.0

                    sims = mcc_vectors @ vsic_vec / (mcc_norms * vsic_norm)
                    # Lấy trực tiếp top-N của cosine làm dummy rerank
                    top_n_idxs = np.argsort(sims)[-self.rerank_top_n:][::-1]
                    for k in range(self.rerank_top_n):
                        if k < len(top_n_idxs):
                            reranked_mcc_indices[i, k] = top_n_idxs[k]
                            # Rerank score fallback to cosine score
                            rerank_scores[i, k] = sims[top_n_idxs[k]]
                        else:
                            reranked_mcc_indices[i, k] = -1
                            rerank_scores[i, k] = 0.0

            mcc_codes = [m["mcc"] for m in mcc_entries]
            vsic_codes = [v["code"] for v in vsic_entries]

            zero_mcc_codes = [mcc_codes[idx] for idx in mcc_zero]
            zero_vsic_codes = [vsic_codes[idx] for idx in vsic_zero]
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
                reranked_mcc_indices=reranked_mcc_indices,
                rerank_scores=rerank_scores,
                meta={
                    "dim": dim,
                    "zero_vector_codes": {
                        "mcc": zero_mcc_codes,
                        "vsic": zero_vsic_codes,
                    },
                    "embedding_model": self.embedding_model,
                    "reranker_model": self.reranker_model,
                    "rerank_top_n": self.rerank_top_n,
                    "cosine_top_k": self.cosine_top_k,
                    "artifact_version": 2,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
            )

            EmbeddingArtifactRepository().write(output, artifact)
            logger.info(
                f"Wrote embedding artifact to {output} "
                f"(mcc {mcc_vectors.shape}, vsic {vsic_vectors.shape}, rerank {reranked_mcc_indices.shape})"
            )
            return 0

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return 1
        except RuntimeError as e:
            logger.error(f"Runtime / model error: {e}")
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
            (matrix of shape ``(len(texts), dim)``, list of zero-vector
            indices).
        """
        vectors: List[List[float]] = []
        zero_indices: List[int] = []
        dim = None
        with tqdm(total=len(texts), desc=f"Embedding {label}") as pbar:
            for i, text in enumerate(texts):
                try:
                    vec = client.embed([text])[0]
                    if not vec or any(np.isnan(vec)):
                        raise ValueError("empty or NaN embedding")
                    if dim is None:
                        dim = len(vec)
                    vectors.append(list(vec))
                except (RuntimeError, ValueError) as e:
                    logger.warning(
                        f"{label} embedding failed at index {i} "
                        f"— using zero vector. Error: {e}"
                    )
                    if dim is None:
                        # Fallback dimension estimation if first item fails
                        dim = 2560 if "Qwen" in getattr(client, "model_name", "") else 1024
                    vectors.append([0.0] * dim)
                    zero_indices.append(i)
                pbar.update(1)

        return np.array(vectors, dtype=np.float32), zero_indices
