"""Use case for mapping VSIC codes to MCC codes using 2-stage retrieval."""

import json
import re
import time as _time
from typing import Generator

import numpy as np
from loguru import logger
from tqdm import tqdm

# #region agent log helpers
import os as _os
_DEBUG_LOG = _os.path.join(
    "/content/drive/MyDrive/projects/mcc-lens"
    if _os.path.isdir("/content/drive/MyDrive/projects/mcc-lens")
    else _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
    ".cursor", "debug-c603c2.log"
)

def _dblog(msg: str, data: dict, hypothesis: str) -> None:
    _os.makedirs(_os.path.dirname(_DEBUG_LOG), exist_ok=True)
    entry = json.dumps({"sessionId": "c603c2", "timestamp": int(_time.time() * 1000), "location": "map_vsic_to_mcc_use_case.py", "message": msg, "data": data, "hypothesisId": hypothesis})
    with open(_DEBUG_LOG, "a") as _f:
        _f.write(entry + "\n")
# #endregion

from app.models.mapping_entry import MappingEntry, RankedMcc
from app.services.llm_prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.mcc_code_validator import MccCodeValidator
from app.services.protocols import (
    EmbeddingClient,
    LLMClient,
    MappingCheckpointRepository,
)


class MapVsicToMccUseCase:
    """
    Orchestrates the 2-stage mapping pipeline:
    1. Embedding pre-filter to get top-K MCC candidates
    2. LLM re-ranking to select top-3 with explanations
    """

    LOW_SCORE_THRESHOLD = 0.5

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from text. Returns empty string if input is None/empty."""
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        llm_client: LLMClient,
        checkpoint_repo: MappingCheckpointRepository,
        vsic_entries: list[dict],
        mcc_entries: list[dict],
        validator: MccCodeValidator,
    ) -> None:
        """Initialize use case with dependencies."""
        self.embedding_client = embedding_client
        self.llm_client = llm_client
        self.checkpoint_repo = checkpoint_repo
        self.vsic_entries = vsic_entries
        self.mcc_entries = mcc_entries
        self.validator = validator

    def execute(
        self, top_k: int = 15, resume: bool = False
    ) -> Generator[MappingEntry, None, None]:
        """
        Execute the mapping pipeline for all VSIC entries.

        Args:
            top_k: Number of top MCC candidates to send to LLM.
            resume: Whether to resume from checkpoint.

        Yields:
            MappingEntry for each processed VSIC.
        """
        logger.info(f"Starting mapping pipeline with top_k={top_k}, resume={resume}")

        # Load checkpoint if resuming
        completed = {}
        if resume:
            completed = self.checkpoint_repo.load()
            logger.info(
                f"Resuming from checkpoint with {len(completed)} completed entries"
            )

        # Precompute MCC embeddings with batching and progress bar
        logger.info("Precomputing MCC embeddings...")
        mcc_texts = []
        for mcc in self.mcc_entries:
            title = self._strip_html(mcc["title"])
            description = self._strip_html(mcc.get("description") or "")
            text = f"{title} — {description[:500]}"
            mcc_texts.append(text)

        # Batch size reduced to 8 to avoid Ollama NaN errors on batches
        # where total token count across mixed-length texts exceeds the
        # bge-m3 internal limit, causing a 500 with "unsupported value: NaN".
        batch_size = 8
        mcc_embeddings = []

        with tqdm(total=len(mcc_texts), desc="Computing MCC embeddings") as pbar:
            for i in range(0, len(mcc_texts), batch_size):
                batch = mcc_texts[i : i + batch_size]
                # #region agent log H-B/H-C: scan batch for suspicious entries before embed
                suspicious = [{"global_idx": i+j, "mcc_raw": self.mcc_entries[i+j], "text": t, "text_len": len(t)} for j, t in enumerate(batch) if not t.strip() or len(t) > 400]
                if suspicious:
                    _dblog("mcc_batch_suspicious_entries", {"batch_start": i, "suspicious": suspicious}, "H-B/H-C")
                # #endregion
                batch_embeddings = self.embedding_client.embed(batch)
                mcc_embeddings.extend(batch_embeddings)
                pbar.update(len(batch))

        logger.info(f"Computed embeddings for {len(mcc_embeddings)} MCC entries")

        # Precompute normalized MCC matrix for vectorized cosine similarity
        self._mcc_matrix = np.array(mcc_embeddings)
        self._mcc_norms = np.linalg.norm(self._mcc_matrix, axis=1)
        self._mcc_norms[self._mcc_norms == 0] = 1.0  # Avoid division by zero

        # Process each VSIC
        for vsic in self.vsic_entries:
            vsic_code = vsic["code"]
            vsic_title = vsic["title"]

            # Skip if already completed
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

            # Embed VSIC title
            vsic_embedding = self.embedding_client.embed([vsic_title])[0]

            # Compute cosine similarity with all MCC (vectorized)
            vsic_arr = np.array(vsic_embedding)
            vsic_norm = float(np.linalg.norm(vsic_arr))
            if vsic_norm == 0:
                vsic_norm = 1.0

            # Dot product with normalized MCC matrix
            sim_scores = self._mcc_matrix @ vsic_arr / (self._mcc_norms * vsic_norm)
            similarities = [(float(sim), i) for i, sim in enumerate(sim_scores)]

            # Get top-K candidates
            similarities.sort(reverse=True, key=lambda x: x[0])
            top_k_similarities = similarities[:top_k]

            # Adaptive Top-K Escalation: double top_k and retry if LLM returns
            # empty or its top-1 score is low (hard cases need more candidates)
            current_top_k = top_k
            ranked_results: list = []
            while True:
                top_k_slice = similarities[:current_top_k]
                score_map = {idx: sim for sim, idx in top_k_slice}
                candidate_indices = [idx for _, idx in top_k_slice]

                candidates = []
                for idx in candidate_indices:
                    mcc = self.mcc_entries[idx]
                    candidates.append(
                        {
                            "mcc": mcc["mcc"],
                            "title": self._strip_html(mcc["title"]),
                            "description": self._strip_html(
                                mcc.get("description") or ""
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
                next_top_k = current_top_k * 2
                max_allowed_top_k = len(self.mcc_entries)

                if needs_escalation and current_top_k < max_allowed_top_k:
                    current_top_k = min(next_top_k, max_allowed_top_k)
                    logger.info(
                        f"VSIC '{vsic_code}': escalating top_k "
                        f"to {current_top_k} "
                        f"(empty={not ranked_results}, score={top1_llm_score:.2f})"
                    )
                else:
                    break

            # Build mapping entry
            entry = MappingEntry(
                vsic_code=vsic_code,
                vsic_title=vsic_title,
                top_results=ranked_results,
            )

            # Save checkpoint
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
