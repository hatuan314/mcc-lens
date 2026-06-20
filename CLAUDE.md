# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Principle: CLAUDE.md must be short and prunable — only what Claude cannot infer from code

# MCC Lens — Python CLI

VSIC → MCC mapping toolkit. Converts Visa MCC reference images (OCR) and VSIC Excel into JSON, then maps Vietnamese VSIC industry codes to Visa MCC codes via a 2-stage embedding + LLM pipeline.

## Commands
```bash
python3 -m venv venv && source venv/bin/activate   # setup
pip install -r requirements.txt                    # install deps
python3 main.py <command>                           # run a CLI subcommand
pytest                                              # run all tests (config in pytest.ini)
black app/                                           # format (line-length 88)
flake8 app/                                          # lint (.flake8)
mypy app/                                            # type-check (py3.9, ignore_missing_imports)
```

CLI subcommands (argparse, dispatched in `main.py`): `convert-mcc`, `convert-vsic`, `convert-vsic-2025`, `embed`, `map-vsic-mcc`. See README.md for full flag matrix and output schemas.

## Testing
- Run a single test: `pytest tests/test_mapping_controller.py::TestName::test_case -v`
- `pytest` auto-runs coverage on `app/` (`--cov`, `--strict-markers`); HTML report lands in `htmlcov/`
- No network in unit tests — Ollama/WokuShop clients and Surya OCR are stubbed at the client boundary
- `main.py` exits with `0` on success, `1` on any exception — controllers return the exit code

## Architecture (MVC + Clean Architecture, dependency rule inward)
- `app/models/` — entities (`mcc_entry`, `vsic_entry`, `vsic_2025_entry`, `mapping_entry`, `ocr_line`); no I/O
- `app/repositories/` — all I/O: Excel/JSON read-write, image loading, checkpoints, and LLM/embedding clients (`ollama_*`, `wokushop_*`)
- `app/services/` — business logic; `map_vsic_to_mcc_use_case.py` orchestrates the pipeline; `protocols.py` defines the client interfaces (typing.Protocol) that decouple services from concrete repos
- `app/controllers/` — wire repos+services together and return an exit code
- `app/views/` — output formatting (`progress_bar_view`)

Flow: `main.py` (parse args, instantiate deps) → controller (`.execute()`) → use-case/service → repository. Manual dependency injection, no framework. Inner layers (models/services) never import outer layers; services depend on `protocols.py` abstractions, not concrete clients.

### The 3-stage pipeline (`embed` → `map-vsic-mcc`)
The pipeline runs in 3 stages across two commands sharing one self-contained `.npz` artifact version 2:
- **`embed` (producer, run on Colab/GPU)** — `EmbedController` reads MCC+VSIC JSON, generates embeddings via Qwen3-Embedding (dynamic dim, read from meta) and performs reranking via Qwen3-Reranker in-process (sentence-transformers). The top-K cosine similarities (default 100) are reranked, and top-N reranked indices and scores (default 20) are saved directly into the artifact.
- **`map-vsic-mcc` (consumer, run locally — no embedding/reranking)** — `MappingController` loads the artifact via `EmbeddingArtifactRepository` (hard-fails if version != 2 or wrong dim), then `MapVsicToMccUseCase.execute` reads the pre-computed rerank indices directly to build candidates for the LLM. No cosine or heavy compute is done locally. Number of candidates sent to LLM is controlled by `llm_n` (default 10, clamped <= `rerank_top_n` from artifact).
Outputs two xlsx files (simple top-1, detailed top-3 + commentary). Per-VSIC checkpoint enables `--resume`. The artifact is the **sole source of the work set** — `map-vsic-mcc` no longer reads source JSON and takes `--embeddings <path>` instead of `--vsic-input`/`--mcc-input`.

## LLM providers
- Selected by `LLM_PROVIDER` env var (`ollama` | `wokushop`), read via `app/config.py` `Config`
- **Embeddings come from the `.npz` artifact** (produced by `embed` via Ollama `bge-m3`), NOT computed live during `map-vsic-mcc` — the mapping run needs no embedding client. With the `wokushop` LLM provider it needs no Ollama at all; with the `ollama` LLM provider only the LLM model is required (health-check via `check_ollama_llm`).
- WokuShop is an OpenAI-compatible proxy (uses the `openai` SDK); requires `WOKUSHOP_API_KEY`. `Config.validate()` raises at import time if the key is missing when provider is `wokushop`
- When provider is `wokushop`, `--llm-model` is ignored; the model comes from `WOKUSHOP_MODEL`

## Non-obvious conventions
- `Config.validate()` runs at **import time** (bottom of `config.py`) — a bad `ENVIRONMENT` or missing WokuShop key fails fast on any import of `app.config`
- Heavy deps (Surya OCR, torch/transformers) are imported **lazily inside command branches** in `main.py` — keep them out of module top-level so unrelated commands stay fast
- Surya OCR runs on Apple MPS natively (no CUDA); first run downloads ~1-2GB weights from HuggingFace
- Logging is `loguru` configured in `main.py:setup_logging()` — log to stderr, never `print()` to stdout for diagnostics
- Code comments/docstrings in this repo are often Vietnamese; match the surrounding file's language
- Keep code files under 200 lines, kebab-case filenames (see `.claude/rules/`)

## Security
- `.env` contains a real `WOKUSHOP_API_KEY` and is gitignored — never commit it, never echo it to logs/stdout
- Validate user-supplied paths before opening; pass `subprocess`/external args as lists, never `shell=True` with interpolation

## See also
- @README.md for CLI flags, output JSON schemas, hardware requirements, and Google Colab setup
- @docs/ai/ for per-feature requirements/design/implementation/testing docs
- @.claude/rules/ for project development + Python style rules (PEP 8, SOLID)
