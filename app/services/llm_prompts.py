"""LLM prompt templates for VSIC to MCC mapping."""

SYSTEM_PROMPT = (
    "Bạn là chuyên gia phân loại ngành. Xếp hạng top-3 MCC phù hợp nhất cho "
    "ngành VSIC. Trả về JSON object đúng định dạng: "
    '{"results": [{"mcc_code": "xxxx", "score": 0.9, "comment": "..."}]}. '
    "Mảng results chứa tối đa 3 phần tử, sắp xếp theo thứ tự phù hợp nhất. "
    "score là điểm số thể hiện độ phù hợp ngữ nghĩa (từ 0.0 đến 1.0): "
    ">= 0.9 (khớp hoàn toàn), 0.7-0.89 (khớp tốt), 0.5-0.69 (liên quan nhưng khác phạm vi), < 0.5 (chỉ khớp một phần). "
    "comment là 1 câu ngắn tiếng Việt giải thích tại sao. "
    'Nếu không có MCC nào phù hợp, trả về {"results": []}. '
    "KHÔNG thêm text ngoài JSON."
)

USER_PROMPT_TEMPLATE = """VSIC Industry (Tiếng Việt):
{vsic_title}

Top-K MCC Candidates (Tiếng Anh):
{candidates}

Please rank the top 3 most suitable MCC codes for this VSIC industry.
"""


def build_user_prompt(vsic_title: str, candidates: list[dict]) -> str:
    """
    Build user prompt with VSIC title and top-K MCC candidates.

    Args:
        vsic_title: VSIC title in Vietnamese.
        candidates: List of candidate dicts with keys: mcc, title, description.

    Returns:
        Formatted user prompt string.
    """
    candidate_text = ""
    for i, cand in enumerate(candidates, 1):
        desc = (cand.get("description") or "")[:200]
        candidate_text += (
            f"{i}. MCC: {cand['mcc']} - {cand['title']}\n   Description: {desc}\n"
        )

    return USER_PROMPT_TEMPLATE.format(
        vsic_title=vsic_title,
        candidates=candidate_text,
    )
