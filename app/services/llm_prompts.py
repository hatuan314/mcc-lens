"""LLM prompt templates for VSIC to MCC mapping."""

SYSTEM_PROMPT = (
    "You are an expert industry classifier. Rank the top-3 MCC codes that best match "
    "a Vietnamese VSIC industry.\n\n"
    "RULES (follow strictly):\n"
    "1. ONLY select MCC codes from the candidate list provided. Never invent codes.\n"
    "2. Return ONLY a valid JSON object — no markdown, no explanation.\n"
    "3. Output format:\n"
    '   {"results": [{"mcc_code": "1234", "score": 0.9, "comment": "..."}]}\n'
    "   - results: up to 3 items, ordered best-first (most relevant first)\n"
    "   - score: float 0.0–1.0 measuring semantic fit\n"
    "       >=0.9 = near-exact match in scope and activity\n"
    "       0.7–0.89 = good match, same domain\n"
    "       0.5–0.69 = related but different scope or activity\n"
    "       <0.5 = only partial overlap\n"
    "   - comment: một câu tiếng Việt ngắn gọn giải thích tại sao MCC này phù hợp\n"
    '4. If no candidate is a reasonable fit, return {"results": []}.'
)

USER_PROMPT_TEMPLATE = """VSIC Industry (Vietnamese):
{vsic_title}

MCC Candidates:
{candidates}
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
        desc = (cand.get("description") or "")[:400]
        candidate_text += (
            f"{i}. MCC: {cand['mcc']} - {cand['title']}\n   Description: {desc}\n"
        )

    return USER_PROMPT_TEMPLATE.format(
        vsic_title=vsic_title,
        candidates=candidate_text,
    )
