"""Use case for mapping VSIC codes to MCC codes from a pre-reranked artifact.

Consumer-only: embeddings and rerank order are read from a pre-built artifact
(produced by the `embed` command); this use case never embeds or reranks. It
reads the artifact's top-N reranked MCC candidates per VSIC and sends them to
the LLM for final selection + Vietnamese commentary.
"""

import json
from typing import Generator, Optional

from loguru import logger

from app.models.embedding_artifact import EmbeddingArtifact
from app.models.mapping_entry import MappingEntry, RankedMcc
from app.services.embed_text_builder import strip_html
from app.services.llm_prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.mcc_code_validator import MccCodeValidator
from app.services.protocols import LLMClient, MappingCheckpointRepository


class MapVsicToMccUseCase:
    """
    Orchestrates the final mapping stage over a pre-reranked artifact:
    read top-N reranked MCC candidates → LLM selects top-3 with explanations.
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
        self, llm_n: int = 10, resume: bool = False, limit: Optional[int] = None, top_k: Optional[int] = None
    ) -> Generator[MappingEntry, None, None]:
        """
        Execute the mapping pipeline for all VSIC entries in the artifact.

        Args:
            llm_n: Number of top MCC candidates from rerank to send to LLM.
            resume: Whether to resume from checkpoint.
            limit: Process only the first ``limit`` VSIC entries (None = all).
            top_k: Legacy alias for llm_n.

        Yields:
            MappingEntry for each processed VSIC.
        """
        if top_k is not None:
            llm_n = top_k
        logger.info(f"Starting mapping pipeline with llm_n={llm_n}, resume={resume}")

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

        # Iterate over VSIC entries from the artifact; --limit slices the loop.
        vsic_iter = list(zip(self.artifact.vsic_codes, self.artifact.vsic_titles))
        if limit is not None:
            vsic_iter = vsic_iter[:limit]

        for i, (vsic_code, vsic_title) in enumerate(vsic_iter):
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

            # Load top candidates and scores directly from artifact rerank results
            idxs = self.artifact.reranked_mcc_indices[i][:llm_n]
            scores = self.artifact.rerank_scores[i][:llm_n]

            candidates = []
            for k, idx in enumerate(idxs):
                if idx == -1:
                    continue  # skip padding
                candidates.append(
                    {
                        "mcc": self.artifact.mcc_codes[idx],
                        "title": strip_html(self.artifact.mcc_titles[idx]),
                        "description": strip_html(self.artifact.mcc_descriptions[idx] or ""),
                        "score": float(scores[k]),
                    }
                )

            if not candidates:
                logger.warning(f"No candidates found for VSIC {vsic_code}")
                ranked_results = []
            else:
                user_prompt = build_user_prompt(vsic_title, candidates)
                llm_response = self.llm_client.chat(SYSTEM_PROMPT, user_prompt)
                ranked_results = self._parse_llm_response(llm_response, candidates)

            # Fallback if LLM returns empty response
            if not ranked_results and candidates:
                ranked_results = []
                for k in range(min(3, len(candidates))):
                    cand = candidates[k]
                    ranked_results.append(
                        RankedMcc(
                            mcc_code=cand["mcc"],
                            mcc_title=cand["title"],
                            score=round(float(cand["score"]), 2),
                            comment="",
                        )
                    )

            if ranked_results and ranked_results[0].score < self.LOW_SCORE_THRESHOLD:
                logger.warning(
                    f"VSIC '{vsic_code}': top-1 score thấp ({ranked_results[0].score:.2f}) — cần review"
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

    def _parse_llm_response(
        self, response: str, candidates: list[dict]
    ) -> list[RankedMcc]:
        """
        Parse LLM response into RankedMcc objects.

        Args:
            response: LLM JSON response string.
            candidates: Original candidates with scores.

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
                                    "fallback to rerank score"
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
