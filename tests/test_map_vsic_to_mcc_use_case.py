"""Unit tests for MapVsicToMccUseCase."""

import json
from typing import Dict

import numpy as np

from app.models.embedding_artifact import EmbeddingArtifact
from app.services.map_vsic_to_mcc_use_case import MapVsicToMccUseCase
from app.services.mcc_code_validator import MccCodeValidator

_DIM = 8


def _unit_vectors(n: int) -> np.ndarray:
    """n identical unit vectors → cosine = 1.0 for all (no escalation)."""
    if n == 0:
        return np.zeros((0, _DIM), dtype=np.float32)
    return np.array([[1.0] + [0.0] * (_DIM - 1) for _ in range(n)], dtype=np.float32)


# ---------------------------------------------------------------------------
# Fake clients
# ---------------------------------------------------------------------------


class FakeLLMClient:
    """Returns configurable JSON responses."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list = []

    def chat(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.calls.append({"system": system, "user": user})
        return self.response


class FakeCheckpointRepo:
    def __init__(self, initial: Dict = None) -> None:
        self._data: Dict = initial or {}
        self.saves: list = []

    def load(self) -> Dict:
        return dict(self._data)

    def save(self, vsic_code: str, result: Dict) -> None:
        self._data[vsic_code] = result
        self.saves.append(vsic_code)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VSIC_ENTRIES = [
    {"code": "0111", "title": "Trồng lúa"},
    {"code": "6201", "title": "Lập trình máy vi tính"},
    {"code": "4711", "title": "Bán lẻ lương thực"},
]

# 5 VSIC thực tế đầu tiên từ output/vsic-vn.json
REAL_VSIC_ENTRIES = [
    {"code": "1110", "title": "Trồng lúa", "level": 4, "parent_code": None, "description": ""},
    {"code": "1120", "title": "Trồng ngô và cây lương thực có hạt khác", "level": 4, "parent_code": None, "description": ""},
    {"code": "1130", "title": "Trồng cây lấy củ có chất bột", "level": 4, "parent_code": None, "description": ""},
    {"code": "1140", "title": "Trồng cây mía", "level": 4, "parent_code": None, "description": ""},
    {"code": "1150", "title": "Trồng cây thuốc lá, thuốc lào", "level": 4, "parent_code": None, "description": ""},
]

MCC_ENTRIES = [
    {"mcc": "0111", "title": "Farms", "description": "Crop farming"},
    {"mcc": "7372", "title": "Computer Programming", "description": "Software"},
    {"mcc": "5411", "title": "Grocery Stores", "description": "Food retail"},
    {"mcc": "5999", "title": "Misc Retail", "description": "General retail"},
    {"mcc": "7299", "title": "Other Services", "description": "Personal services"},
]

VALID_MCC_CODES = [m["mcc"] for m in MCC_ENTRIES]

VALID_LLM_RESPONSE = json.dumps(
    [
        {"mcc_code": "0111", "comment": "Agriculture direct match"},
        {"mcc_code": "5411", "comment": "Food related"},
        {"mcc_code": "5999", "comment": "General fallback"},
    ]
)


def _make_artifact(vsic_entries: list, mcc_entries: list) -> EmbeddingArtifact:
    """Build an in-memory artifact with identical unit vectors and rerank data."""
    n_vsic = len(vsic_entries)
    n_mcc = len(mcc_entries)
    rerank_top_n = min(n_mcc, 5) if n_mcc > 0 else 0
    
    # Generate mock rerank indices and scores
    reranked_mcc_indices = np.zeros((n_vsic, rerank_top_n), dtype=np.int32)
    for i in range(n_vsic):
        for k in range(rerank_top_n):
            reranked_mcc_indices[i, k] = k % n_mcc if n_mcc > 0 else -1
            
    rerank_scores = np.ones((n_vsic, rerank_top_n), dtype=np.float32) * 0.95

    return EmbeddingArtifact(
        mcc_vectors=_unit_vectors(len(mcc_entries)),
        mcc_codes=[m["mcc"] for m in mcc_entries],
        mcc_titles=[m["title"] for m in mcc_entries],
        mcc_descriptions=[m.get("description") or "" for m in mcc_entries],
        vsic_vectors=_unit_vectors(len(vsic_entries)),
        vsic_codes=[v["code"] for v in vsic_entries],
        vsic_titles=[v["title"] for v in vsic_entries],
        reranked_mcc_indices=reranked_mcc_indices,
        rerank_scores=rerank_scores,
        meta={
            "dim": _DIM,
            "zero_vector_codes": {"mcc": [], "vsic": []},
            "artifact_version": 2,
            "rerank_top_n": rerank_top_n,
        },
    )


def _make_use_case(
    llm_response: str = VALID_LLM_RESPONSE,
    checkpoint_data: Dict = None,
    vsic_entries: list = None,
    mcc_entries: list = None,
) -> tuple:
    checkpoint_repo = FakeCheckpointRepo(checkpoint_data or {})
    llm_client = FakeLLMClient(llm_response)
    mcc_entries = MCC_ENTRIES if mcc_entries is None else mcc_entries
    vsic_entries = VSIC_ENTRIES if vsic_entries is None else vsic_entries
    validator = MccCodeValidator([m["mcc"] for m in mcc_entries])
    artifact = _make_artifact(vsic_entries, mcc_entries)
    use_case = MapVsicToMccUseCase(
        llm_client=llm_client,
        checkpoint_repo=checkpoint_repo,
        artifact=artifact,
        validator=validator,
    )
    return use_case, llm_client, checkpoint_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_yields_one_entry_per_vsic(self) -> None:
        use_case, _, _ = _make_use_case()
        results = list(use_case.execute(top_k=3))
        assert len(results) == len(VSIC_ENTRIES)

    def test_entry_has_correct_vsic_code_and_title(self) -> None:
        use_case, _, _ = _make_use_case()
        results = list(use_case.execute(top_k=3))
        codes = {r.vsic_code for r in results}
        assert codes == {"0111", "6201", "4711"}

    def test_entry_top_results_up_to_3(self) -> None:
        use_case, _, _ = _make_use_case()
        results = list(use_case.execute(top_k=5))
        for entry in results:
            assert len(entry.top_results) <= 3

    def test_each_ranked_mcc_has_valid_score(self) -> None:
        use_case, _, _ = _make_use_case()
        results = list(use_case.execute(top_k=3))
        for entry in results:
            for rank in entry.top_results:
                assert 0.0 <= rank.score <= 1.0

    def test_checkpoint_saved_for_each_vsic(self) -> None:
        use_case, _, checkpoint_repo = _make_use_case()
        list(use_case.execute(top_k=3))
        assert set(checkpoint_repo.saves) == {"0111", "6201", "4711"}


class TestNoMatch:
    def test_empty_llm_response_falls_back_to_rerank(self) -> None:
        use_case, _, _ = _make_use_case(llm_response="[]")
        results = list(use_case.execute(top_k=3))
        for entry in results:
            assert len(entry.top_results) == 3
            assert entry.top_results[0].mcc_code == "0111"
            assert entry.top_results[0].comment == ""
            assert entry.top_results[0].score == 0.95

    def test_invalid_json_falls_back_to_rerank(self) -> None:
        use_case, _, _ = _make_use_case(llm_response="not json")
        results = list(use_case.execute(top_k=3))
        for entry in results:
            assert len(entry.top_results) == 3
            assert entry.top_results[0].mcc_code == "0111"

    def test_llm_returns_non_list_falls_back_to_rerank(self) -> None:
        use_case, _, _ = _make_use_case(llm_response='{"mcc_code": "0111"}')
        results = list(use_case.execute(top_k=3))
        for entry in results:
            assert len(entry.top_results) == 3
            assert entry.top_results[0].mcc_code == "0111"


class TestHallucination:
    def test_hallucinated_mcc_code_falls_back_to_top1_embedding(self) -> None:
        bad_response = json.dumps(
            [
                {"mcc_code": "FAKE", "comment": "hallucinated"},
            ]
        )
        use_case, _, _ = _make_use_case(llm_response=bad_response)
        results = list(use_case.execute(top_k=3))
        for entry in results:
            # Should fallback to top-1 embedding which IS in valid list
            for rank in entry.top_results:
                assert rank.mcc_code in VALID_MCC_CODES


class TestResume:
    def test_resume_skips_completed_vsic(self) -> None:
        # 2 of 3 already done
        checkpoint_data = {
            "0111": {
                "top_results": [
                    {
                        "mcc_code": "0111",
                        "mcc_title": "Farms",
                        "score": 0.9,
                        "comment": "ok",
                    }
                ]
            },
            "6201": {
                "top_results": [
                    {
                        "mcc_code": "7372",
                        "mcc_title": "IT",
                        "score": 0.95,
                        "comment": "exact",
                    }
                ]
            },
        }
        use_case, llm_client, _ = _make_use_case(checkpoint_data=checkpoint_data)
        results = list(use_case.execute(top_k=3, resume=True))
        # LLM only called for 1 remaining VSIC
        assert len(llm_client.calls) == 1
        assert len(results) == 3

    def test_resume_false_ignores_checkpoint(self) -> None:
        checkpoint_data = {
            "0111": {
                "top_results": [
                    {
                        "mcc_code": "0111",
                        "mcc_title": "Farms",
                        "score": 0.9,
                        "comment": "ok",
                    }
                ]
            },
        }
        use_case, llm_client, _ = _make_use_case(checkpoint_data=checkpoint_data)
        list(use_case.execute(top_k=3, resume=False))
        # All 3 VSIC processed by LLM even though 1 was in checkpoint
        assert len(llm_client.calls) == 3


class TestEmptyInput:
    def test_empty_vsic_list_returns_no_entries(self) -> None:
        use_case, _, _ = _make_use_case(vsic_entries=[])
        results = list(use_case.execute(top_k=3))
        assert results == []

    def test_does_not_crash_on_empty_vsic(self) -> None:
        use_case, _, _ = _make_use_case(vsic_entries=[])
        list(use_case.execute(top_k=3))  # should not raise


class TestTopKCandidates:
    def test_top_k_limits_candidates_sent_to_llm(self) -> None:
        use_case, llm_client, _ = _make_use_case()
        list(use_case.execute(top_k=2))
        # Verify each user prompt contains at most 2 candidates
        for call in llm_client.calls:
            user_prompt = call["user"]
            # Count "MCC:" occurrences in prompt
            mcc_count = user_prompt.count("MCC:")
            assert mcc_count <= 2

    def test_low_score_threshold_constant(self) -> None:
        assert MapVsicToMccUseCase.LOW_SCORE_THRESHOLD == 0.5


class TestRealVSICEntries:
    """Test với 5 mã VSIC thực tế đầu tiên từ output/vsic-vn.json."""

    def test_processes_5_real_vsic_entries(self) -> None:
        """Xác nhận pipeline xử lý được 5 VSIC thực tế."""
        use_case, _, _ = _make_use_case(vsic_entries=REAL_VSIC_ENTRIES)
        results = list(use_case.execute(top_k=3))
        assert len(results) == 5

    def test_real_vsic_codes_preserved(self) -> None:
        """Xác nhận mã VSIC thực tế được giữ nguyên trong output."""
        use_case, _, _ = _make_use_case(vsic_entries=REAL_VSIC_ENTRIES)
        results = list(use_case.execute(top_k=3))
        codes = {r.vsic_code for r in results}
        expected_codes = {"1110", "1120", "1130", "1140", "1150"}
        assert codes == expected_codes

    def test_real_vsic_titles_preserved(self) -> None:
        """Xác nhận title tiếng Việt của VSIC thực tế được giữ nguyên."""
        use_case, _, _ = _make_use_case(vsic_entries=REAL_VSIC_ENTRIES)
        results = list(use_case.execute(top_k=3))
        titles = {r.vsic_title for r in results}
        expected_titles = {
            "Trồng lúa",
            "Trồng ngô và cây lương thực có hạt khác",
            "Trồng cây lấy củ có chất bột",
            "Trồng cây mía",
            "Trồng cây thuốc lá, thuốc lào",
        }
        assert titles == expected_titles

    def test_real_vsic_checkpoint_saved(self) -> None:
        """Xác nhận checkpoint được lưu cho 5 VSIC thực tế."""
        use_case, _, checkpoint_repo = _make_use_case(vsic_entries=REAL_VSIC_ENTRIES)
        list(use_case.execute(top_k=3))
        assert set(checkpoint_repo.saves) == {"1110", "1120", "1130", "1140", "1150"}

    def test_mcc_matrix_does_not_exist(self) -> None:
        """Xác nhận cosine matrix không còn tồn tại trên use case."""
        use_case, _, _ = _make_use_case()
        list(use_case.execute())
        assert not hasattr(use_case, "_mcc_matrix")
        assert not hasattr(use_case, "_mcc_norms")

    def test_supports_llm_n_parameter(self) -> None:
        """Xác nhận tham số llm_n hoạt động chính xác."""
        use_case, llm_client, _ = _make_use_case()
        list(use_case.execute(llm_n=2))
        for call in llm_client.calls:
            user_prompt = call["user"]
            mcc_count = user_prompt.count("MCC:")
            assert mcc_count <= 2


# ---------------------------------------------------------------------------
# Additional coverage for new Qwen3 migration branches
# ---------------------------------------------------------------------------


def _make_artifact_with_padding(vsic_entries: list, mcc_entries: list) -> EmbeddingArtifact:
    """Artifact where all reranked indices are -1 (no valid candidates)."""
    n_vsic = len(vsic_entries)
    rerank_top_n = 3
    reranked_mcc_indices = np.full((n_vsic, rerank_top_n), -1, dtype=np.int32)
    rerank_scores = np.zeros((n_vsic, rerank_top_n), dtype=np.float32)
    return EmbeddingArtifact(
        mcc_vectors=np.zeros((len(mcc_entries), _DIM), dtype=np.float32),
        mcc_codes=[m["mcc"] for m in mcc_entries],
        mcc_titles=[m["title"] for m in mcc_entries],
        mcc_descriptions=[m.get("description") or "" for m in mcc_entries],
        vsic_vectors=np.zeros((n_vsic, _DIM), dtype=np.float32),
        vsic_codes=[v["code"] for v in vsic_entries],
        vsic_titles=[v["title"] for v in vsic_entries],
        reranked_mcc_indices=reranked_mcc_indices,
        rerank_scores=rerank_scores,
        meta={
            "dim": _DIM,
            "zero_vector_codes": {"mcc": [], "vsic": []},
            "artifact_version": 2,
            "rerank_top_n": rerank_top_n,
        },
    )


def _make_artifact_low_score(vsic_entries: list, mcc_entries: list) -> EmbeddingArtifact:
    """Artifact with very low rerank scores (< LOW_SCORE_THRESHOLD=0.5)."""
    n_vsic = len(vsic_entries)
    n_mcc = len(mcc_entries)
    rerank_top_n = min(n_mcc, 3)
    reranked_mcc_indices = np.zeros((n_vsic, rerank_top_n), dtype=np.int32)
    for i in range(n_vsic):
        for k in range(rerank_top_n):
            reranked_mcc_indices[i, k] = k % n_mcc
    rerank_scores = np.full((n_vsic, rerank_top_n), 0.2, dtype=np.float32)
    return EmbeddingArtifact(
        mcc_vectors=np.ones((n_mcc, _DIM), dtype=np.float32),
        mcc_codes=[m["mcc"] for m in mcc_entries],
        mcc_titles=[m["title"] for m in mcc_entries],
        mcc_descriptions=[m.get("description") or "" for m in mcc_entries],
        vsic_vectors=np.ones((n_vsic, _DIM), dtype=np.float32),
        vsic_codes=[v["code"] for v in vsic_entries],
        vsic_titles=[v["title"] for v in vsic_entries],
        reranked_mcc_indices=reranked_mcc_indices,
        rerank_scores=rerank_scores,
        meta={
            "dim": _DIM,
            "zero_vector_codes": {"mcc": ["0111"], "vsic": []},
            "artifact_version": 2,
            "rerank_top_n": rerank_top_n,
        },
    )


class TestLimitParameter:
    def test_limit_slices_vsic_entries(self) -> None:
        use_case, llm_client, _ = _make_use_case()
        results = list(use_case.execute(top_k=3, limit=1))
        assert len(results) == 1
        assert len(llm_client.calls) == 1

    def test_limit_zero_returns_no_entries(self) -> None:
        use_case, llm_client, _ = _make_use_case()
        results = list(use_case.execute(top_k=3, limit=0))
        assert results == []
        assert len(llm_client.calls) == 0


class TestPaddingIndices:
    def test_all_minus1_indices_yields_empty_top_results(self) -> None:
        """All reranked indices == -1 → no candidates → empty top_results."""
        checkpoint_repo = FakeCheckpointRepo()
        llm_client = FakeLLMClient(VALID_LLM_RESPONSE)
        validator = MccCodeValidator([m["mcc"] for m in MCC_ENTRIES])
        artifact = _make_artifact_with_padding(VSIC_ENTRIES[:1], MCC_ENTRIES)
        use_case = MapVsicToMccUseCase(
            llm_client=llm_client,
            checkpoint_repo=checkpoint_repo,
            artifact=artifact,
            validator=validator,
        )
        results = list(use_case.execute(llm_n=3))
        assert len(results) == 1
        assert results[0].top_results == []
        # LLM not called when no candidates
        assert len(llm_client.calls) == 0


class TestZeroVectorWarning:
    def test_zero_vector_meta_still_yields_results(self) -> None:
        """Artifact with zero_vector_codes in meta still processes all VSIC."""
        checkpoint_repo = FakeCheckpointRepo()
        llm_client = FakeLLMClient(VALID_LLM_RESPONSE)
        validator = MccCodeValidator([m["mcc"] for m in MCC_ENTRIES])
        artifact = _make_artifact_low_score(VSIC_ENTRIES, MCC_ENTRIES)
        # meta has zero_vector_codes.mcc = ["0111"] → should log warning on execute
        use_case = MapVsicToMccUseCase(
            llm_client=llm_client,
            checkpoint_repo=checkpoint_repo,
            artifact=artifact,
            validator=validator,
        )
        results = list(use_case.execute(llm_n=3))
        assert len(results) == len(VSIC_ENTRIES)


class TestLowScoreWarning:
    def test_low_rerank_score_still_returns_results(self) -> None:
        """Score < LOW_SCORE_THRESHOLD logs warning but result is still returned."""
        checkpoint_repo = FakeCheckpointRepo()
        # LLM returns a match without explicit score → uses candidate score (0.2)
        llm_client = FakeLLMClient(VALID_LLM_RESPONSE)
        validator = MccCodeValidator([m["mcc"] for m in MCC_ENTRIES])
        artifact = _make_artifact_low_score(VSIC_ENTRIES, MCC_ENTRIES)
        use_case = MapVsicToMccUseCase(
            llm_client=llm_client,
            checkpoint_repo=checkpoint_repo,
            artifact=artifact,
            validator=validator,
        )
        results = list(use_case.execute(llm_n=3))
        # Despite low score, results are yielded
        assert len(results) == len(VSIC_ENTRIES)
        for entry in results:
            if entry.top_results:
                assert entry.top_results[0].score < MapVsicToMccUseCase.LOW_SCORE_THRESHOLD


class TestDictWrappedLLMResponse:
    def test_dict_response_with_results_key(self) -> None:
        """LLM returns {"results": [...]} → unwrapped correctly."""
        items = [
            {"mcc_code": "0111", "comment": "Agriculture"},
            {"mcc_code": "5411", "comment": "Food"},
        ]
        response = json.dumps({"results": items})
        use_case, _, _ = _make_use_case(llm_response=response)
        results = list(use_case.execute(top_k=3))
        for entry in results:
            assert len(entry.top_results) >= 1

    def test_dict_response_fallback_to_first_list_value(self) -> None:
        """Dict with unknown key but list value → uses that list."""
        items = [{"mcc_code": "0111", "comment": "ok"}]
        response = json.dumps({"unknown_key": items})
        use_case, _, _ = _make_use_case(llm_response=response)
        results = list(use_case.execute(top_k=3))
        for entry in results:
            assert len(entry.top_results) >= 1

    def test_dict_response_no_list_field_falls_back_to_rerank(self) -> None:
        """Dict with no list-valued key → _parse_llm_response returns [] → fallback."""
        response = json.dumps({"some_key": "string_value", "other_key": 42})
        use_case, _, _ = _make_use_case(llm_response=response)
        results = list(use_case.execute(top_k=3))
        # Fallback to top-3 rerank candidates
        for entry in results:
            assert len(entry.top_results) == 3


class TestNonDictItemInList:
    def test_non_dict_item_in_list_is_skipped(self) -> None:
        """If list contains non-dict items, they are skipped gracefully."""
        response = json.dumps(["not_a_dict", {"mcc_code": "0111", "comment": "ok"}])
        use_case, _, _ = _make_use_case(llm_response=response)
        results = list(use_case.execute(top_k=3))
        for entry in results:
            # "not_a_dict" is skipped; only valid dict items are parsed
            for rank in entry.top_results:
                assert rank.mcc_code in VALID_MCC_CODES


class TestInvalidLLMScore:
    def test_invalid_score_string_falls_back_to_rerank_score(self) -> None:
        """LLM provides non-numeric score → fallback to rerank score from artifact."""
        response = json.dumps([
            {"mcc_code": "0111", "comment": "Agriculture", "score": "not_a_number"},
            {"mcc_code": "5411", "comment": "Food", "score": "bad"},
        ])
        use_case, _, _ = _make_use_case(llm_response=response)
        results = list(use_case.execute(top_k=3))
        for entry in results:
            for rank in entry.top_results:
                # Score must be a valid float (from artifact rerank scores, not LLM)
                assert isinstance(rank.score, float)
                assert 0.0 <= rank.score <= 1.0
