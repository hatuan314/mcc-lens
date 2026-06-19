# Brainstorm: Split Embedding & LLM Re-rank into 2 Independent Modules

- **Date:** 2026-06-19 (revised — supersedes earlier "embedding cache" direction)
- **Status:** Brainstorm complete — pending implementation plan
- **Scope:** Split the `map-vsic-mcc` pipeline into 2 independent producer/consumer modules so the GPU-heavy embedding step runs on Google Colab and the LLM re-rank step runs locally via WokuShop API.

## Problem Statement

`MapVsicToMccUseCase.execute()` currently mixes two concerns in one run:
1. **Embedding** — precompute 91 MCC vectors (batch_size=1) + embed each VSIC inside the loop, via `bge-m3` on Ollama. GPU-heavy; source of the NaN/GPU-corruption workarounds.
2. **LLM re-rank** — cosine top-K then LLM top-3.

Local machine has no good GPU and hits the NaN issue. Embedding belongs on Colab (free GPU); re-rank belongs on the paid WokuShop API. Coupling them forces Ollama to run wherever mapping runs.

**Supersedes** the earlier in-pipeline "embedding cache" idea (`.npz` cache auto-detected inside the use case). That approach is dropped — replaced by an explicit producer/consumer split with a downloadable artifact.

## Decisions (confirmed with user)

| Decision | Choice |
|----------|--------|
| Relationship to old cache feature | **Replace** — drop the in-use-case auto-cache idea entirely |
| Embed scope | Both MCC + VSIC (full sets) |
| Architecture | 2 independent modules: `embed` (Colab/GPU) → artifact → `map-vsic-mcc` (local/WokuShop) |
| Handoff | Colab writes artifact to Google Drive → user downloads file → feeds module 2 |
| Artifact content | **Self-contained**: vectors + code + title + description (module 2 needs no source JSON) |
| `map-vsic-mcc` | Refactor to **consumer-only** — never embeds |
| Missing/corrupt artifact | **Hard-fail** with a clear message ("run embed on Colab first"); local needs no Ollama |

## Architecture

```
┌─ MODULE 1: embed  (Colab, GPU) ──────────────┐
│  MCC.json + VSIC.json                         │
│      ↓ bge-m3 (Ollama on Colab GPU)           │
│  embed-artifact.npz   (→ Google Drive)        │
└───────────────────────────────────────────────┘
                  ↓  (user downloads the file)
┌─ MODULE 2: map-vsic-mcc  (local, no GPU) ─────┐
│  embed-artifact.npz                            │
│      ↓ cosine similarity → top-K               │
│      ↓ LLM re-rank (WokuShop API)              │
│  vsic-mcc-mapping.xlsx + ...-detail.xlsx       │
└───────────────────────────────────────────────┘
```

Key consequence: the **artifact is the source of truth for the work set**. Module 2 processes exactly the entries present in the artifact — there is no "partial cache / missing entry" branch, so no Ollama fallback and no embedder dependency locally.

## Artifact Format (self-contained `.npz`)

Single `.npz` carrying both MCC and VSIC, each as parallel arrays:

```
embed-artifact.npz
├── mcc_vectors      np.float32 (91, 1024)
├── mcc_codes        list[str]
├── mcc_titles       list[str]
├── mcc_descriptions list[str]
├── vsic_vectors     np.float32 (N, 1024)
├── vsic_codes       list[str]
├── vsic_titles      list[str]
└── meta             {embedding_model, dim, mcc_source, vsic_source, created_at}
```

- `bge-m3` is **1024-dim** (not 3072 — earlier doc was wrong; code fallback also uses 1024).
- `np.savez` stores arrays + object arrays in one file; load with `np.load(allow_pickle=True)`.
- Module 2 validates `meta.dim == vectors.shape[1]` and that MCC/VSIC arrays are non-empty; otherwise hard-fail.
- Zero-vector rows (failed `bge-m3` NaN) are still written but flagged; module 2 logs a warning. (Open: decide whether embed should abort vs. emit-with-warning — see Open Questions.)

## Module 1: `embed`

- New entry point `embed.py` (standalone, runs on Colab) — minimal deps: `ollama`, `numpy`, `loguru`.
- Reuses `OllamaEmbeddingClient` (batch_size=1, NaN reset/retry logic already there).
- Reads MCC.json + VSIC.json, builds the same text strings module 2's prompt expects (`title — description[:500]` for MCC; VSIC title), embeds all, writes `.npz` to `--output` (default a Drive path on Colab).
- No LLM, no Excel, no checkpoint. Pure producer.

## Module 2: `map-vsic-mcc` (refactored, consumer-only)

- Drops MCC precompute loop and per-VSIC `embedding_client.embed()`. `MapVsicToMccUseCase` no longer takes an `EmbeddingClient`.
- New input: `--embeddings <artifact.npz>`. Loads vectors + text from artifact.
- Builds `_mcc_matrix` from `mcc_vectors`; iterates `vsic_codes`/`vsic_vectors`; cosine top-K → LLM re-rank (unchanged) → checkpoint → Excel.
- WokuShop is the LLM provider; **Ollama no longer required locally**. Embedding health-check removed from this command.

## Files to Change

| File | Change |
|------|--------|
| `embed.py` (new) | Module 1 entry point — load JSON, embed all, write `.npz` |
| `app/repositories/embedding_artifact_repository.py` (new) | Read/write the self-contained `.npz` (I/O layer) |
| `app/services/map_vsic_to_mcc_use_case.py` | Remove embedding (MCC precompute + per-VSIC embed); accept pre-loaded vectors+text instead of `EmbeddingClient` |
| `app/controllers/mapping_controller.py` | Load artifact instead of building embedding clients; add `--embeddings`; drop embedding health-check; remove `WokuShopEmbeddingClient` usage |
| `main.py` | Add `--embeddings` arg to `map-vsic-mcc`; (embed module may be its own script or a subcommand — see Open Questions) |
| `README.md` / `CLAUDE.md` | Document the 2-stage Colab→local workflow; "embeddings come from the artifact, not live Ollama" |

Cleanup: `app/repositories/wokushop_embedding_client.py` becomes unused (was a pre-existing deviation from "embeddings always Ollama") — flag for removal.

## Quality Note (addresses user concern)

Artifact format (self-contained vs vector-only) has **zero impact on mapping quality** — identical vectors either way. Output quality is driven only by:
- **Embedding model** (`bge-m3`) → top-K candidate recall.
- **LLM model** (WokuShop, default `gpt-4o`) → top-3 re-rank + comments.

The split changes *where* compute runs, not *what* is computed. Quality is byte-identical to running the current coupled pipeline with the same models.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Artifact/JSON version drift | Self-contained artifact carries its own text + `meta.*_source`; module 2 never reads source JSON |
| User edits VSIC.json but forgets to re-run embed | Acceptable — module 2 only maps what's in the artifact; document the workflow |
| `bge-m3` NaN on Colab | Keep batch_size=1 + reset/retry; decide embed abort-vs-warn on zero vectors |
| Breaking change to `map-vsic-mcc` (now needs artifact) | Update README/CLAUDE.md; clear hard-fail message pointing to the embed step |
| Self-contained file size | ~ (91+N) × 1024 × 4 bytes + text ≈ a few MB — negligible |

## Open Questions — RESOLVED (2026-06-19)

1. **Embed packaging:** → `main.py` subcommand (`python3 main.py embed`), not a standalone script. Reuses argparse/loguru/config; runs on Colab & local.
2. **Zero-vector policy in embed:** → write-with-warning; record `zero_vector_codes` in artifact meta. Module 2 warns and still maps them. (Matches current resilient behavior.)
3. **Artifact path defaults:** → reuse `--gdrive-output-dir` on Colab (`<dir>/embed-artifact.npz`); `--embeddings` on local, default `output/embed-artifact.npz`.

## Success Criteria / Validation

- `embed.py` on Colab produces `embed-artifact.npz` with correct shapes (`mcc 91×1024`, `vsic N×1024`) and non-zero vectors.
- `map-vsic-mcc --embeddings artifact.npz` runs **with Ollama stopped**, produces both Excel outputs, matching quality of the current coupled run on the same models.
- Corrupt/missing artifact → clean hard-fail with actionable message, exit code ≠ 0.
- Unit tests stub the artifact repository at the I/O boundary (no network, no Ollama).

## Next Steps

- Confirm the 3 open questions during planning.
- Generate detailed implementation plan (`/execute-plan` precursor) when ready.
