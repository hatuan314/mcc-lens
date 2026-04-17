# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

MCC Lens là dự án Python dùng để chuyển đổi dữ liệu mã ngành (VSIC ↔ MCC). Nguồn dữ liệu MCC gốc là ảnh scan do VISA phát hành (`assets/mcc-visa/`), cần được OCR/parse thành JSON có cấu trúc trước khi dùng cho các pipeline mapping downstream.

## Commands

All shell commands must use `python3` (not `python`) per project convention.

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run app entrypoint
python3 main.py

# Tests — pytest.ini auto-enables coverage (term-missing + html) on app/
pytest                                   # full suite
pytest tests/test_config.py              # single file
pytest tests/test_models.py::TestClass::test_fn  # single test
pytest -k "pattern"                      # by name

# Code quality
black app/        # format (line-length 88, configured in pyproject.toml)
flake8 app/       # lint (extend-ignore E203, W503)
mypy app/         # type check (python_version = 3.8, ignore_missing_imports)
```

Always update `requirements.txt` when importing a new third-party library.

## Architecture

The codebase follows **Clean Architecture + MVC** as mandated by `.claude/rules/python-standards.md`. The layer boundaries are load-bearing — do not cross them:

```
app/
├── models/         # Domain entities & pydantic schemas (innermost layer)
├── services/       # Use cases / business logic — depends only on models + abstractions
├── repositories/   # Data access (files, DB, external APIs)
├── controllers/    # Entry-point coordinators; receive input, invoke services, return to view
└── views/          # Output formatting (CLI progress, JSON response shaping, etc.)
```

**Dependency Rule (strict):** inner layers (`models`, `services`) must not import from outer layers (`repositories`, `controllers`, `views`). Services depend on **Protocols/abstractions** defined alongside them; concrete implementations (e.g. a Florence-2 vision backend, a filesystem JSON writer) are injected by the Controller. When adding a new capability, introduce the Protocol first, then the implementation.

`app/config.py` exposes a `Config` class that reads env vars via `python-dotenv` and self-validates at import time. `main.py` wires `loguru` logging from `Config.LOG_LEVEL` / `Config.LOG_FILE` before dispatching to controllers.

## Feature Development Workflow

This repo drives all non-trivial features through a document-first workflow under `docs/ai/`. A feature named `{name}` gets five synchronized files:

```
docs/ai/requirements/feature-{name}.md   # problem, user stories, acceptance criteria
docs/ai/design/feature-{name}.md         # architecture, data models, interfaces
docs/ai/planning/feature-{name}.md       # task breakdown, dependencies, risks
docs/ai/implementation/feature-{name}.md # implementation notes (filled during coding)
docs/ai/testing/feature-{name}.md        # test plan, coverage targets
```

Templates live at `docs/ai/{phase}/README.md` — copy them (preserving YAML frontmatter + headings) to create feature docs. New feature requests typically arrive as briefs in `docs/ai/orders/`.

Slash commands in `.claude/commands/` automate each phase: `/new-requirement`, `/review-requirements`, `/review-design`, `/execute-plan`, `/check-implementation`, `/update-planning`, `/code-review`, `/writing-test`, `/simplify-implementation`, `/capture-knowledge`, `/remember`, `/debug`. The expected gate order before implementation: **new-requirement → review-requirements → review-design → execute-plan**.

## Coding Standards (project-specific)

From `.claude/rules/python-standards.md`:

- **PEP 8** with type hints on every function signature; docstrings in **Google style**.
- Functions do one thing; prefer ≤ 3 parameters.
- **SOLID** is enforced — especially **D**: depend on abstractions (Protocols), not concretions. When in doubt, add a Protocol in `services/` rather than importing a concrete class across layers.
- Respond to the user in Vietnamese (per global user instructions).

## Notes for Claude

- Subdirectories under `app/` currently contain only `__init__.py` — the scaffolding is intentional; populate them following the layer rules above rather than inventing a new structure.
- `tests/` mirrors `app/` layout. `pytest.ini` already forces `--cov=app`; a test run will fail noisily if coverage collection breaks, which usually means a module import error, not a missing test.
- `docs/ai/orders/*.md` are human-written briefs — read them verbatim when starting a feature; don't paraphrase them into requirements without the `/new-requirement` flow.
