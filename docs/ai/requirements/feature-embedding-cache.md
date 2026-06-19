---
phase: requirements
title: Requirements & Problem Understanding
description: Split embedding and LLM re-rank into 2 independent modules — embed on Colab, map locally via WokuShop
feature: embedding-cache
date: 2026-06-19
---

# Requirements & Problem Understanding — Split Embedding & LLM Re-rank

> **Direction change (2026-06-19):** This supersedes the earlier in-pipeline `.npz` "embedding cache" idea. The new approach splits `map-vsic-mcc` into two independent producer/consumer modules. Source: `docs/ai/orders/brainstorm-embedding-cache-2026-06-19.md`.

## Problem Statement

`MapVsicToMccUseCase.execute()` couples two concerns in a single run:
1. **Embedding** — precompute 91 MCC vectors (batch_size=1) + embed each VSIC inside the loop, via `bge-m3` on Ollama. GPU-heavy; source of the NaN/GPU-corruption workarounds.
2. **LLM re-rank** — cosine top-K then LLM top-3 + comments.

The local machine has no good GPU and hits the NaN issue; embedding should run on **Google Colab** (free GPU). The LLM re-rank should run **locally via the paid WokuShop API**. Coupling forces Ollama to run wherever mapping runs.

**Affected users:** Data engineer/analyst who runs the embedding step on Colab once, downloads the artifact, then runs the mapping step locally without any GPU or Ollama.

**Runtime context (confirmed 2026-06-19):** Embeddings always come from **Ollama `bge-m3` (1024-dim)** — produced on Colab. WokuShop is **LLM-only**, never embeddings. The local mapping run requires **no Ollama**.

## Goals & Objectives

**Primary goals:**
- Split the pipeline into 2 modules sharing a single artifact file:
  - **Module 1 `embed`** — a `main.py` subcommand that embeds ALL MCC + VSIC on Colab and writes one self-contained `.npz` artifact.
  - **Module 2 `map-vsic-mcc`** — refactored to **consumer-only**: read the artifact, cosine top-K, LLM re-rank via WokuShop, write Excel.
- Artifact is the **single source of truth for the work set**: Module 2 maps exactly the entries present in the artifact.
- Local mapping run requires no GPU and no Ollama.

**Secondary goals:**
- **Stage-1 (embedding + cosine top-K) is deterministic and identical** to the current coupled pipeline given the same artifact: same vectors → same cosine → same top-K ordering (verifiable by test).
- **Stage-2 (LLM re-rank) is NOT required to be byte-identical** — it runs on a different provider/model (WokuShop) and is non-deterministic; validated by quality spot-check, not byte equality.
- Output quality is preserved because the artifact carries **all text fields the LLM prompt consumes** (MCC: `mcc`/`title`/`description`; VSIC: `code`/`title`) — see User Stories edge cases. The split changes *where* compute runs, not *what* is computed.

**Non-goals:**
- No in-use-case auto-cache / hash-based invalidation (abandoned — replaced by the explicit artifact).
- No incremental artifact updates — re-run `embed` to refresh.
- No local embedding fallback in Module 2 — artifact missing/corrupt is a hard error.
- No new Protocol abstraction beyond a small artifact I/O repository.

## User Stories & Use Cases

- As a data engineer, I want to run `python3 main.py embed` on Colab to produce one artifact file on Google Drive, so the GPU-heavy work happens off my laptop.
- As a data engineer, I want to download the artifact and run `map-vsic-mcc --embeddings artifact.npz` locally with Ollama stopped, so I only pay for the WokuShop LLM step.
- As a developer, I want Module 2 to drop the `--vsic-input`/`--mcc-input` JSON flags entirely (the artifact is the sole input for text + vectors), so there is no ambiguity about the source of truth.
- As a developer, I want Module 2 to hard-fail with an actionable message when the artifact is missing/corrupt, so I never silently produce wrong output.

**Key workflows:**
1. **Embed (Colab):** load MCC.json + VSIC.json → embed all via `bge-m3` → write `embed-artifact.npz` to `<gdrive-output-dir>/`.
2. **Handoff:** user downloads `embed-artifact.npz` from Drive to the local `output/` dir.
3. **Map (local):** `map-vsic-mcc --embeddings output/embed-artifact.npz` → cosine top-K → WokuShop LLM re-rank → checkpoint → Excel.

**Edge cases (confirmed decisions):**
- **Zero-vector (failed bge-m3 NaN) embeddings** → `embed` still writes the artifact, logs a clear warning with the count, and records `zero_vector_codes` in artifact meta. Module 2 logs a one-time warning for those codes and still maps them. A zero vector yields **cosine similarity exactly 0.0** (NOT NaN): Module 2 keeps the existing norm guards — `mcc_norms[mcc_norms == 0] = 1.0` and `if vsic_norm == 0: vsic_norm = 1.0` — so the entry simply ranks at the bottom. Covered by a unit test (zero-vector MCC → similarity 0, no NaN).
- **Artifact missing / corrupt / wrong dimension** → Module 2 hard-fails with a clear message ("run `embed` on Colab first"), non-zero exit code. No fallback embedding. Hard-fail checklist (checked in order, fail fast):
  1. File not found → "Artifact not found at `<path>`. Run `embed` on Colab first."
  2. Not loadable / not a valid `.npz` → "Artifact corrupt or not a valid .npz."
  3. Missing required key (`mcc_vectors`, `mcc_codes`, `mcc_titles`, `mcc_descriptions`, `vsic_codes`, `vsic_titles`, `vsic_vectors`, `meta`) → list the missing keys.
  4. Wrong dimension: `mcc_vectors.shape[1] != 1024` (and VSIC) → report actual vs expected.
  5. Length mismatch: `len(mcc_codes) != mcc_vectors.shape[0]` (and VSIC) → "Artifact inconsistent: N codes vs M vectors."
- **`--limit` in Module 2** → applies only to the processing loop; the artifact already holds the full set, so limiting never poisons anything.
- **`--resume`** → checkpoint filters which VSICs go through the LLM pass; embeddings always come from the artifact.

## Success Criteria

- `python3 main.py embed` on Colab produces `embed-artifact.npz` with shapes `mcc (91, 1024)` and `vsic (N, 1024)` plus matching code/title/description arrays.
- `map-vsic-mcc --embeddings artifact.npz` runs **with Ollama stopped** and produces both Excel outputs.
- **Stage-1 verifiable:** given the same artifact, Module 2's cosine top-K candidate list matches the coupled pipeline's exactly (deterministic). **Stage-2** LLM output is validated by spot-check on a VSIC sample (business-sensible top-1), not byte equality.
- Missing/corrupt/dimension-mismatched artifact → clean hard-fail per the checklist above, actionable message, exit code ≠ 0.
- Module 2 never instantiates an embedding client; drops `--vsic-input`/`--mcc-input` flags; `WokuShopEmbeddingClient` usage removed.
- All existing tests pass; new unit tests cover artifact read/write, hard-fail paths, and the consumer-only loop.

## Constraints & Assumptions

**Technical constraints:**
- NumPy `.npz` artifact, self-contained (vectors + codes + titles + descriptions + meta), loaded with `np.load(allow_pickle=True)`.
- `meta` kept minimal — `dim` (for the hard-fail dimension check) + `zero_vector_codes`. No `schema_version`/model-version fields: MCC/VSIC source data is effectively static, so format-drift risk is negligible (YAGNI).
- `bge-m3` is **1024-dim** (earlier docs wrongly said 3072; code zero-vector fallback also uses 1024).
- Artifact default path reuses the Colab convention: `<gdrive-output-dir>/embed-artifact.npz` on Colab; `--embeddings` (default `output/embed-artifact.npz`) on local.
- Module 1 reuses `OllamaEmbeddingClient` (batch_size=1 + NaN reset/retry already implemented).

**Assumptions:**
- MCC and VSIC source JSON are authoritative inputs to `embed`; once embedded, the artifact carries its own text so Module 2 never re-reads source JSON.
- User accepts that editing source JSON without re-running `embed` simply means those edits are not reflected (artifact is source of truth).

## Questions & Open Items

**Resolved (2026-06-19):**
- Module/cache relationship → **replace** in-pipeline cache with a 2-module split. ✓
- Embed scope → both MCC + VSIC, full sets. ✓
- Artifact content → self-contained (vector + code + title + description + meta). ✓
- Handoff → Google Drive → user downloads file. ✓
- Module 2 → consumer-only, no Ollama; missing/corrupt → hard-fail. ✓
- Embed packaging → `python3 main.py embed` subcommand (not a standalone script). ✓
- Zero-vector policy → write-with-warning + record `zero_vector_codes` in meta. ✓
- Artifact path → reuse `--gdrive-output-dir` on Colab; `--embeddings` local default `output/embed-artifact.npz`. ✓
- Output quality preserved without source JSON → confirmed: LLM prompt only consumes MCC `mcc`/`title`/`description` + VSIC `code`/`title`, all carried in the artifact. Adding new prompt fields later requires re-running `embed`. ✓
- Module 2 drops `--vsic-input`/`--mcc-input` (artifact is sole input). ✓
- Hard-fail conditions → explicit 5-step checklist (see Edge cases). ✓
- Zero-vector → cosine 0.0 via existing norm guards, not NaN. ✓
- "byte-identical" goal → split into deterministic Stage-1 (verifiable) + spot-check Stage-2. ✓
- Artifact `meta` → minimal (`dim` + `zero_vector_codes`), no versioning fields (YAGNI). ✓

**Cleanup tracked by this feature:**
- `app/repositories/wokushop_embedding_client.py` becomes unused once Module 2 is consumer-only (was a pre-existing deviation from "embeddings always Ollama") → remove.
