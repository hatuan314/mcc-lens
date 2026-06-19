"""Use case for mapping VSIC codes to MCC codes using 2-stage retrieval.

Consumer-only: embeddings are read from a pre-built artifact (produced by the
`embed` command); this use case never embeds anything. Stage 1 is a cosine
top-K pre-filter over the artifact's MCC matrix; Stage 2 is LLM re-ranking.
"""

import json
from typing import Generator, Optional

import numpy as np
from loguru import logger

from app.models.embedding_artifact import EmbeddingArtifact
from app.models.mapping_entry import MappingEntry, RankedMcc
from app.services.embed_text_builder import strip_html
from app.services.llm_prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.mcc_code_validator import MccCodeValidator
from app.services.protocols import LLMClient, MappingCheckpointRepository


class MapVsicToMccUseCase:
    """
    Orchestrates the 2-stage mapping pipeline:
    1. Cosine pre-filter (over artifact MCC vectors) to get top-K candidates
    2. LLM re-ranking to select top-3 with explanations
    """

    LOW_SCORE_THRESHOLD = 0.5

    def __init__(
        self,
        llm_client: LLMClient,
        checkpoint_repo: MappingCheckpointRepository,
        artifact: EmbeddingArtifact,
        validator: MccCodeValidator,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            llm_client: LLM client for re-ranking.
            checkpoint_repo: Checkpoint repository for resume support.
            artifact: Pre-built embedding artifact (sole source of vectors + text).
            validator: MCC code validator.
        """
        self.llm_client = llm_client
        self.checkpoint_repo = checkpoint_repo
        self.artifact = artifact
        self.validator = validator

    def execute(
        self, top_k: int = 15, resume: bool = False, limit: Optional[int] = None
    ) -> Generator[MappingEntry, None, None]:
        """
        Execute the mapping pipeline for all VSIC entries in the artifact.

        Args:
            top_k: Number of top MCC candidates to send to LLM.
            resume: Whether to resume from checkpoint.
            limit: Process only the first ``limit`` VSIC entries (None = all).

        Yields:
            MappingEntry for each processed VSIC.
        """
        logger.info(f"Starting mapping pipeline with top_k={top_k}, resume={resume}")

        completed = {}
        if resume:
            completed = self.checkpoint_repo.load()
            logger.info(
                f"Resuming from checkpoint with {len(completed)} completed entries"
            )

        # Warn once about zero-vector entries recorded by the producer.
        zero_codes = self.artifact.meta.get("zero_vector_codes", {})
        if zero_codes.get("mcc") or zero_codes.get("vsic"):
            logger.warning(
                f"Artifact has zero-vector embeddings (rank low): "
                f"MCC {zero_codes.get('mcc', [])}, VSIC {zero_codes.get('vsic', [])}"
            )

        # Precomputed normalized MCC matrix for vectorized cosine similarity.
        self._mcc_matrix = np.asarray(self.artifact.mcc_vectors)
        self._mcc_norms = np.linalg.norm(self._mcc_matrix, axis=1)
        self._mcc_norms[self._mcc_norms == 0] = 1.0  # Avoid division by zero

        n_mcc = len(self.artifact.mcc_codes)

        # Iterate over VSIC entries from the artifact; --limit slices the loop.
        vsic_iter = list(
            zip(
                self.artifact.vsic_codes,
                self.artifact.vsic_titles,
                self.artifact.vsic_vectors,
            )
        )
        if limit is not None:
            vsic_iter = vsic_iter[:limit]

        for vsic_code, vsic_title, vsic_vector in vsic_iter:
            if vsic_code in completed:
                logger.debug(f"Skipping VSIC {vsic_code} (already completed)")
                result_data = completed[vsic_code]
                top_results = [
                    RankedMcc(**r) for r in result_data.get("top_results", [])
                ]
                yield MappingEntry(
                    vsic_code=vsic_code, vsic_title=vsic_title, top_results=top_results
                )
                continue

            # Cosine similarity with all MCC (vectorized) — no embedding call.
            vsic_arr = np.asarray(vsic_vector)
            vsic_norm = float(np.linalg.norm(vsic_arr))
            if vsic_norm == 0:
                vsic_norm = 1.0

            sim_scores = self._mcc_matrix @ vsic_arr / (self._mcc_norms * vsic_norm)
            similarities = [(float(sim), i) for i, sim in enumerate(sim_scores)]
            similarities.sort(reverse=True, key=lambda x: x[0])

            ranked_results = self._rerank_with_escalation(
                vsic_code, vsic_title, similarities, top_k, n_mcc
            )

            entry = MappingEntry(
                vsic_code=vsic_code,
                vsic_title=vsic_title,
                top_results=ranked_results,
            )

            checkpoint_data = {"top_results": [r.model_dump() for r in ranked_results]}
            self.checkpoint_repo.save(vsic_code, checkpoint_data)

            yield entry

        logger.info("Mapping pipeline completed")

    def _rerank_with_escalation(
        self,
        vsic_code: str,
        vsic_title: str,
        similarities: list,
        top_k: int,
        n_mcc: int,
    ) -> list:
        """LLM re-rank with adaptive top-K escalation.

        Doubles top_k and retries if the LLM returns empty or a low top-1 score
        (hard cases need more candidates).
        """
        current_top_k = top_k
        ranked_results: list = []
        while True:
            top_k_slice = similarities[:current_top_k]
            score_map = {idx: sim for sim, idx in top_k_slice}
            candidate_indices = [idx for _, idx in top_k_slice]

            candidates = []
            for idx in candidate_indices:
                candidates.append(
                    {
                        "mcc": self.artifact.mcc_codes[idx],
                        "title": strip_html(self.artifact.mcc_titles[idx]),
                        "description": strip_html(
                            self.artifact.mcc_descriptions[idx] or ""
                        ),
                        "score": score_map[idx],
                    }
                )

            user_prompt = build_user_prompt(vsic_title, candidates)
            llm_response = self.llm_client.chat(SYSTEM_PROMPT, user_prompt)
            ranked_results = self._parse_llm_response(llm_response, candidates)

            top1_llm_score = ranked_results[0].score if ranked_results else 0.0
            needs_escalation = (
                not ranked_results or top1_llm_score < self.LOW_SCORE_THRESHOLD
            )

            if needs_escalation and current_top_k < n_mcc:
                current_top_k = min(current_top_k * 2, n_mcc)
                logger.info(
                    f"VSIC '{vsic_code}': escalating top_k to {current_top_k} "
                    f"(empty={not ranked_results}, score={top1_llm_score:.2f})"
                )
            else:
                break

        return ranked_results

    def _parse_llm_response(
        self, response: str, candidates: list[dict]
    ) -> list[RankedMcc]:
        """
        Parse LLM response into RankedMcc objects.

        Args:
            response: LLM JSON response string.
            candidates: Original top-K candidates with scores.

        Returns:
            List of RankedMcc objects (max 3).
        """
        try:
            parsed = json.loads(response)

            # Accept bare list or wrapped object {"results": [...]} /
            # {"mcc_codes": [...]}
            if isinstance(parsed, dict):
                items = None
                for key in ("results", "mcc_codes", "mccs", "data"):
                    if isinstance(parsed.get(key), list):
                        items = parsed[key]
                        break
                if items is None:
                    # Fallback: first list-valued key
                    for v in parsed.values():
                        if isinstance(v, list):
                            items = v
                            break
                if items is None:
                    logger.warning(f"LLM response has no list field: {response}")
                    return []
                parsed = items

            if not isinstance(parsed, list):
                logger.warning(f"LLM response is not a list: {response}")
                return []

            ranked_results = []
            for item in parsed[:3]:
                if not isinstance(item, dict):
                    continue
                mcc_code = item.get("mcc_code", "")
                comment = item.get("comment", "")
                llm_score = item.get("score")

                # Find original candidate to get title and score
                original = next((c for c in candidates if c["mcc"] == mcc_code), None)
                if original:
                    # Validate MCC code
                    valid_mcc = self.validator.validate(mcc_code, candidates[0]["mcc"])
                    if valid_mcc:
                        final_score = original["score"]
                        if llm_score is not None:
                            try:
                                final_score = float(llm_score)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid LLM score '{llm_score}' for "
                                    f"MCC {mcc_code}, "
                                    "fallback to cosine score"
                                )

                        ranked_results.append(
                            RankedMcc(
                                mcc_code=valid_mcc,
                                mcc_title=original["title"],
                                score=round(float(final_score), 2),
                                comment=comment,
                            )
                        )
                    else:
                        logger.warning(
                            f"Invalid MCC {mcc_code} after validation, skipping"
                        )
                else:
                    logger.warning(
                        f"LLM hallucinated MCC {mcc_code} "
                        "not in candidate list, skipping"
                    )

            return ranked_results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}. Response: {response}")
            return []
