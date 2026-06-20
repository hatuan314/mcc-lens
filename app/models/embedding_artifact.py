"""Embedding artifact entity — self-contained embedding output for the
2-module split (embed producer → map-vsic-mcc consumer)."""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


@dataclass
class EmbeddingArtifact:
    """Self-contained embedding artifact shared between the ``embed`` producer
    and the ``map-vsic-mcc`` consumer.

    Carries every text field the LLM prompt consumes (MCC code/title/description,
    VSIC code/title) so the consumer never re-reads the source JSON.

    Attributes:
        mcc_vectors: MCC embedding matrix, shape ``(n_mcc, dim)``.
        mcc_codes: MCC code strings, length ``n_mcc``.
        mcc_titles: MCC titles, length ``n_mcc``.
        mcc_descriptions: MCC descriptions, length ``n_mcc``.
        vsic_vectors: VSIC embedding matrix, shape ``(n_vsic, dim)``.
        vsic_codes: VSIC code strings, length ``n_vsic``.
        vsic_titles: VSIC titles, length ``n_vsic``.
        reranked_mcc_indices: Per-VSIC reranked MCC row indices, shape
            ``(n_vsic, rerank_top_n)``; ``-1`` marks padding.
        rerank_scores: Cross-encoder scores aligned with
            ``reranked_mcc_indices``, shape ``(n_vsic, rerank_top_n)``.
        meta: Metadata dict; functional keys: ``dim``, ``artifact_version``,
            ``rerank_top_n``, ``zero_vector_codes``. ``embedding_model``,
            ``reranker_model``, ``cosine_top_k``, ``created_at`` are labels.
    """

    mcc_vectors: np.ndarray
    mcc_codes: List[str]
    mcc_titles: List[str]
    mcc_descriptions: List[str]
    vsic_vectors: np.ndarray
    vsic_codes: List[str]
    vsic_titles: List[str]
    reranked_mcc_indices: np.ndarray = field(default_factory=lambda: np.array([]))
    rerank_scores: np.ndarray = field(default_factory=lambda: np.array([]))
    meta: Dict = field(default_factory=dict)
