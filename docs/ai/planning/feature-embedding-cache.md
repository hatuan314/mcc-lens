---
phase: planning
title: Project Planning & Task Breakdown
description: Implementation plan for splitting embedding (Colab) and LLM re-rank (local) into 2 modules
feature: embedding-cache
date: 2026-06-19
---

# Project Planning & Task Breakdown — Split Embedding & LLM Re-rank

## Milestones

- [ ] Milestone 1: Artifact model + repository implemented and unit-tested (read/write/validate)
- [ ] Milestone 2: Module 1 `embed` subcommand produces a valid artifact
- [ ] Milestone 3: Module 2 `map-vsic-mcc` refactored to consumer-only (no embedding client, runs with Ollama stopped)
- [ ] Milestone 4: Old embedding-client path removed; docs + `.gitignore` updated; full test suite green

## Task Breakdown

### Phase 1: Artifact Model & Repository

- [ ] Task 1.1: Add `app/models/embedding_artifact.py` — `EmbeddingArtifact` dataclass (mcc/vsic vectors + codes + titles + descriptions + meta)
- [ ] Task 1.2: Add `app/repositories/embedding_artifact_repository.py`
  - `write(path, artifact)` → `np.savez` all arrays + JSON-encoded meta
  - `read(path)` → `np.load(allow_pickle=True)`; raise `FileNotFoundError` if missing; raise `ValueError` on dim mismatch / empty arrays / corrupt file

### Phase 2: Module 1 — `embed` subcommand

- [ ] Task 2.1: Add `app/controllers/embed_controller.py` — load MCC.json + VSIC.json, build embed texts (reuse `_strip_html` + `title — description[:500]` for MCC, title for VSIC), embed via `OllamaEmbeddingClient` (batch_size=1), collect `zero_vector_codes`, write artifact
- [ ] Task 2.2: Wire `embed` subcommand in `main.py` — args: `--mcc-input`, `--vsic-input`, `--output`, `--gdrive-output-dir`, `--ollama-host`, `--embedding-model`; resolve artifact path (gdrive override)
- [ ] Task 2.3: Log clear warning + count when any zero-vector occurs; still write artifact

### Phase 3: Module 2 — `map-vsic-mcc` consumer-only

- [ ] Task 3.1: Change `MapVsicToMccUseCase.__init__` — drop `embedding_client`, accept `artifact: EmbeddingArtifact`
- [ ] Task 3.2: Refactor `execute()` — build `_mcc_matrix` from `artifact.mcc_vectors`; build `vsic_code -> vector` map; loop does lookup (remove MCC precompute + per-VSIC embed); pull MCC title/description for prompt from artifact arrays
- [ ] Task 3.3: In `MappingController.execute()` — add `--embeddings` (default `output/embed-artifact.npz`, gdrive override); load artifact via repo; on `FileNotFoundError`/`ValueError` log error + return non-zero exit
- [ ] Task 3.4: Remove embedding-client construction + embedding health-check from controller; keep WokuShop LLM health-check
- [ ] Task 3.5: Wire `--embeddings` arg in `main.py` for `map-vsic-mcc`

### Phase 4: Cleanup, Config & Docs

- [ ] Task 4.1: Delete `app/repositories/wokushop_embedding_client.py` (now unused); remove its imports
- [ ] Task 4.2: Add `output/*.npz` to `.gitignore`
- [ ] Task 4.3: Update `README.md` + `CLAUDE.md` — document the 2-stage Colab→local workflow; "embeddings come from the artifact, not live Ollama"; `map-vsic-mcc` now requires `--embeddings`

### Phase 5: Tests

- [ ] Task 5.1: `EmbeddingArtifactRepository` — write→read round-trip; corrupt file → `ValueError`; missing → `FileNotFoundError`; dim mismatch → `ValueError`
- [ ] Task 5.2: `EmbedController` — produces artifact with correct shapes; zero-vector recorded in meta + warning logged
- [ ] Task 5.3: `MapVsicToMccUseCase` — consumes artifact, makes zero embedding calls, lookup matches artifact vectors
- [ ] Task 5.4: `MappingController` — missing/corrupt artifact → non-zero exit; no embedding client constructed
- [ ] Task 5.5: Update existing `test_mapping_controller.py` / use-case tests for new constructor signature

## Dependencies

- Phase 2 + Phase 3 depend on Phase 1 (artifact model + repo)
- Task 3.2 depends on Task 3.1 (constructor signature)
- Task 4.1 depends on Phase 3 (controller no longer references embedding clients)
- Phase 5 tests can be written TDD-style alongside each phase

**External dependencies:** None — `numpy`, `json`, `pathlib`, `loguru`, `ollama` already available.

## Timeline & Estimates

| Phase | Estimated effort |
|-------|-----------------|
| Phase 1 (artifact model + repo) | ~1 hour |
| Phase 2 (embed subcommand) | ~1.5 hours |
| Phase 3 (consumer-only refactor) | ~1.5 hours |
| Phase 4 (cleanup + docs) | ~1 hour |
| Phase 5 (tests) | ~1.5 hours |
| **Total** | **~6.5 hours** |

## Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Breaking change: `map-vsic-mcc` now requires `--embeddings` | High (by design) | Clear hard-fail message + README/CLAUDE.md update pointing to `embed` step |
| `np.load(allow_pickle=True)` warning in future NumPy | Low | Internal artifact only; add explaining comment |
| bge-m3 NaN on Colab leaves zero vectors | Medium | Write-with-warning + `zero_vector_codes` in meta; Module 2 warns and continues |
| VSIC entry with no valid text fails before loop | Low | Module 1 handles empty text at embed time; artifact carries result |
| Artifact/source JSON drift if user edits JSON without re-embedding | Medium | Artifact is source of truth by design; documented in README |

## Resources Needed

- Colab runtime with GPU + Ollama (`bge-m3`) for Module 1 validation
- Local machine with WokuShop API key for Module 2 validation
- Test fixtures: `tmp_path` (pytest), mock `EmbeddingClient`, small synthetic artifact
