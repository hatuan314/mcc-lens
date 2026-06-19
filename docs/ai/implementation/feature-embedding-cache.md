---
phase: implementation
title: Implementation Guide
description: Technical implementation notes for the 2-module split (embed producer + map consumer)
feature: embedding-cache
date: 2026-06-19
---

# Implementation Guide — Split Embedding & LLM Re-rank

## Development Setup

No new dependencies. Libraries already in `requirements.txt`:
- `numpy` — `.npz` save/load
- `ollama` — `bge-m3` embeddings (Module 1, on Colab)
- `loguru` — warnings (zero-vector, hard-fail)
- `json`, `pathlib`, `dataclasses` — stdlib

## Code Structure

```
app/
├── models/
│   └── embedding_artifact.py            ← NEW: EmbeddingArtifact dataclass
├── repositories/
│   ├── embedding_artifact_repository.py ← NEW: .npz read/write/validate
│   └── wokushop_embedding_client.py     ← DELETE (now unused)
├── controllers/
│   ├── embed_controller.py              ← NEW: Module 1 orchestration
│   └── mapping_controller.py            ← load artifact, --embeddings, drop embedding client
└── services/
    └── map_vsic_to_mcc_use_case.py      ← consumer-only: drop EmbeddingClient
main.py                                  ← add `embed` subcommand + `--embeddings`
.gitignore                               ← add output/*.npz
```

## Implementation Notes

### `EmbeddingArtifact` model

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class EmbeddingArtifact:
    mcc_vectors: np.ndarray
    mcc_codes: list[str]
    mcc_titles: list[str]
    mcc_descriptions: list[str]
    vsic_vectors: np.ndarray
    vsic_codes: list[str]
    vsic_titles: list[str]
    meta: dict
```

### `EmbeddingArtifactRepository`

```python
def write(self, path: Path, a: EmbeddingArtifact) -> None:
    np.savez(
        path,
        mcc_vectors=a.mcc_vectors, mcc_codes=np.array(a.mcc_codes, dtype=object),
        mcc_titles=np.array(a.mcc_titles, dtype=object),
        mcc_descriptions=np.array(a.mcc_descriptions, dtype=object),
        vsic_vectors=a.vsic_vectors, vsic_codes=np.array(a.vsic_codes, dtype=object),
        vsic_titles=np.array(a.vsic_titles, dtype=object),
        meta=np.array(json.dumps(a.meta), dtype=object),
    )

def read(self, path: Path) -> EmbeddingArtifact:
    if not path.exists():
        raise FileNotFoundError(
            f"Embedding artifact not found: {path}. Run `python3 main.py embed` on Colab first."
        )
    try:
        data = np.load(path, allow_pickle=True)  # allow_pickle for object string arrays
        meta = json.loads(str(data["meta"]))
        mcc_vectors = data["mcc_vectors"]
        vsic_vectors = data["vsic_vectors"]
    except Exception as e:
        raise ValueError(f"Corrupt embedding artifact {path}: {e}") from e
    if mcc_vectors.size == 0 or vsic_vectors.size == 0:
        raise ValueError(f"Embedding artifact {path} has empty MCC or VSIC vectors")
    if mcc_vectors.shape[1] != meta.get("dim") or vsic_vectors.shape[1] != meta.get("dim"):
        raise ValueError(
            f"Artifact dim mismatch: meta={meta.get('dim')}, "
            f"mcc={mcc_vectors.shape[1]}, vsic={vsic_vectors.shape[1]}"
        )
    return EmbeddingArtifact(mcc_vectors, list(data["mcc_codes"]), ...)
```

### Module 1 — `EmbedController`

```python
# Build texts exactly as the LLM prompt expects (mirror use-case _strip_html logic):
mcc_texts = [f"{strip(m['title'])} — {strip(m.get('description') or '')[:500]}" for m in mcc]
vsic_texts = [v["title"] for v in vsic]

# Embed batch_size=1 (NaN workaround already in OllamaEmbeddingClient.embed)
mcc_vectors, mcc_zero = self._embed_all(mcc_texts)
vsic_vectors, vsic_zero = self._embed_all(vsic_texts)

meta = {
    "embedding_model": self.embedding_model, "dim": dim,
    "mcc_source": str(mcc_input), "vsic_source": str(vsic_input),
    "created_at": datetime.utcnow().isoformat(),
    "zero_vector_codes": {"mcc": mcc_zero, "vsic": vsic_zero},
}
if mcc_zero or vsic_zero:
    logger.warning(
        f"Zero-vector embeddings: {len(mcc_zero)} MCC, {len(vsic_zero)} VSIC "
        f"— artifact written, those codes flagged in meta"
    )
self.artifact_repo.write(output_path, EmbeddingArtifact(...))
```

`_embed_all` calls `embedding_client.embed([text])[0]` per text; on `RuntimeError` (all retries failed) appends `[0.0]*dim` and records the code in the zero list (mirrors current `execute()` fallback).

### Module 2 — `MapVsicToMccUseCase` (consumer-only)

```python
# BEFORE (in execute): precompute MCC + per-loop embed
# AFTER:
self._mcc_matrix = self.artifact.mcc_vectors
self._mcc_norms = np.linalg.norm(self._mcc_matrix, axis=1)
self._mcc_norms[self._mcc_norms == 0] = 1.0
vsic_vec_map = dict(zip(self.artifact.vsic_codes, self.artifact.vsic_vectors))
# MCC text for prompts from artifact (index-aligned with mcc_codes):
mcc_title = self.artifact.mcc_titles[idx]
mcc_desc = self.artifact.mcc_descriptions[idx]

# Inside loop:
vsic_arr = np.array(vsic_vec_map[vsic_code])  # no Ollama call
```

The candidate-building block uses `artifact.mcc_codes[idx] / mcc_titles[idx] / mcc_descriptions[idx]` instead of `self.mcc_entries[idx]`. Cosine + escalation + `_parse_llm_response` logic is unchanged.

### `MappingController.execute()`

```python
artifact = self.artifact_repo.read(embeddings_path)  # raises -> caught below
...
use_case = MapVsicToMccUseCase(
    llm_client=llm_client, checkpoint_repo=checkpoint_repo,
    artifact=artifact, vsic_entries=vsic_entries, validator=validator,
)
```

Remove `OllamaEmbeddingClient` / `WokuShopEmbeddingClient` construction and `check_ollama_embedding`. Keep `check_ollama_models` only for the (rare) Ollama LLM provider; for WokuShop keep the `models.list()` ping.

## Integration Points

- `main.py` `embed` subcommand resolves output to `<gdrive-output-dir>/embed-artifact.npz` when `--gdrive-output-dir` is set, else `--output`.
- `map-vsic-mcc` resolves `--embeddings` similarly (gdrive override → `embed-artifact.npz` under that dir).

## Error Handling

| Failure | Strategy |
|---------|----------|
| Artifact missing | `read()` raises `FileNotFoundError` → controller returns exit 1, actionable message |
| Artifact corrupt | `read()` raises `ValueError` → controller returns exit 1 |
| Dim mismatch | `read()` raises `ValueError` → controller returns exit 1 |
| Zero-vector at embed (Module 1) | Write artifact + warn + record in meta (never abort) |
| `vsic_code` missing from artifact map | Should not happen (artifact = full set); if it does, `KeyError` surfaces a real bug — do not swallow |

## Performance Considerations

- Module 2: no embedding phase. Cost = `np.load` + cosine + LLM calls only.
- Memory: `_mcc_matrix` + `vsic_vec_map` hold all vectors (same magnitude as current `_mcc_matrix`); fine for N < 5000.
- Disk: `(91 + N) × 1024 × 4 bytes` + text ≈ a few MB.

## Security Notes

- Artifact holds only float vectors + public industry text — no PII/secrets.
- `.gitignore` `output/*.npz` prevents accidental commit.
- WokuShop key stays in `.env`; Module 2 never logs it.
