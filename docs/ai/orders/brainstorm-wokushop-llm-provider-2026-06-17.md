# Brainstorm: Replace Ollama/qwen2.5 LLM re-ranker with WokuShop API

- **Date:** 2026-06-17
- **Status:** Brainstorm complete — pending implementation plan
- **Scope decided:** Replace ONLY the LLM re-rank step. Keep `bge-m3` embedding local.

## Problem Statement

VSIC→MCC mapping uses a 2-stage pipeline:
1. **Embedding retrieval** (`bge-m3` via Ollama) → top-K MCC candidates by cosine similarity.
2. **LLM re-rank** (`qwen2.5:14b` via Ollama) → selects top-3, emits JSON.

Motivations to move off Ollama (confirmed with user): mapping quality, speed/infra
offload, GPU cost. Candidate replacement: WokuShop (`https://llm.wokushop.com`), an
OpenAI- and Anthropic-compatible reseller proxy.

## Constraints / Inputs

- Scale: **< 500 VSIC entries** (one-off batch) → token cost negligible.
- Data sensitivity: public industry-classification data → third-party proxy acceptable.
- Architecture already clean: DI via Protocols in `app/services/protocols.py`
  (`LLMClient.chat()`, `EmbeddingClient.embed()`). Use case is provider-agnostic.

## Evaluated Approaches

### A. Replace only LLM re-rank, keep bge-m3 local — CHOSEN
- **Pros:** Surgical. New `WokuShopLLMClient(LLMClient)` (~40 LOC). Use case untouched.
  Quality gain via gpt-4o/claude. Keep `OllamaLLMClient` for instant fallback.
- **Cons:** Embedding still on Ollama. If left on GPU, the "cut GPU/infra" goal is only
  partially met, and the NaN/GPU-corruption workarounds remain.
- **Mitigation:** Run `bge-m3` on **CPU** (Ollama CPU or sentence-transformers). At this
  scale CPU is sufficient, removes GPU dependency entirely, and likely eliminates the NaN
  issue (which is GPU-corruption, not algorithmic).

### B. Replace both LLM + embedding via WokuShop
- **Pros:** Fully eliminates Ollama.
- **Cons:** WokuShop doc lists only chat models — **embedding support unconfirmed**.
  Switching embedding model forces full MCC re-embed and changes retrieval quality.
  Rejected for now.

### C. Call OpenAI/Anthropic directly (no reseller)
- **Pros:** Higher reliability, clearer ToS/privacy.
- **Cons:** More expensive; user explicitly chose the affordable reseller. Kept as
  alternative if proxy proves unreliable (same OpenAI-compatible client, just swap base_url).

## Recommended Solution (Approach A + CPU embedding)

### Model choice (re-rank)
Configurable via env. Recommendation ranking for this task (Vietnamese input, strict JSON,
quality-first, <500 calls):
1. `gpt-4o` — strong reasoning + guaranteed `json_object`. ~15–25 USD total. **Default.**
2. `gpt-4o-mini` — reliable JSON, ~1–2 USD. Budget option.
3. `claude-sonnet-4-6` — strong reasoning; must verify `json_object` via the proxy shim.
4. `gemini-2.0-flash` — 1M context could fit ALL candidates in one prompt and remove the
   escalation loop; verify JSON/quality on Vietnamese.

(WokuShop live pricing not machine-readable — SPA. Confirm exact reseller prices on
`llm.wokushop.com/pricing`; also check for DeepSeek/Qwen large as cheap alternatives.)

### Implementation surface
1. `app/repositories/wokushop_llm_client.py` — `WokuShopLLMClient(LLMClient)`:
   `openai` SDK, `base_url=https://llm.wokushop.com/v1`,
   `response_format={"type":"json_object"}`, `temperature=0`, reuse 3-retry pattern.
2. `app/config.py` — add `LLM_PROVIDER` (`ollama`|`wokushop`), `WOKUSHOP_API_KEY`,
   `WOKUSHOP_BASE_URL`, `WOKUSHOP_MODEL`. API key in `.env` (never commit).
3. `app/controllers/mapping_controller.py` — select `OllamaLLMClient` vs
   `WokuShopLLMClient` by config; when provider=wokushop, replace LLM health-check with a
   cheap `models.list()` ping; keep embedding health-check.
4. Optionally move `bge-m3` to CPU to drop GPU entirely.
5. `requirements.txt` — add `openai`.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Reseller reliability / longevity | Keep `OllamaLLMClient`; switch via env. Same client works against OpenAI/Anthropic direct. |
| `json_object` unsupported on non-OpenAI models via proxy | Smoke-test before full run; existing `_parse_llm_response` is already tolerant of wrapped/bare lists. Prefer gpt-4o* for guaranteed JSON. |
| Escalation loop multiplies calls/cost | Negligible at <500; optionally use a large-context model (gemini) to avoid escalation. |
| API key leakage | `.env` only, gitignored; never log key. |
| Embedding NaN persists | Run bge-m3 on CPU. |

## Success Criteria / Validation

- Smoke test: 1 call returns parseable JSON matching `_parse_llm_response` shape.
- Run on a 10–20 VSIC sample; compare top-3 vs current qwen2.5 output for quality.
- Full <500 run completes; cost matches estimate (single-digit to low-tens USD).
- Fallback verified: flip `LLM_PROVIDER=ollama` and pipeline still runs.

## Next Steps

- Obtain WokuShop API key; confirm pricing + embedding availability on dashboard.
- Smoke-test chosen model for `json_object`.
- (Deferred per user) Generate detailed implementation plan when ready.
