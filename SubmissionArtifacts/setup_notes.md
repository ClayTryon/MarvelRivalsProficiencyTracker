# Setup Notes — ProfTracker Week 8
**Course:** AI 410 | **Author:** Clay Tryon

---

## Prerequisites

- Windows 10/11 (64-bit)
- Python 3.11+ (3.13 recommended — used in CI)
- [uv](https://docs.astral.sh/uv/) — fast Python package manager (preferred)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on PATH
- Free Groq API key: https://console.groq.com (no credit card required)

---

## Environment Setup (uv — recommended)

```powershell
# Install uv if you don't have it
irm https://astral.sh/uv/install.ps1 | iex

# From the ProficiencyTracker root:
uv sync                    # creates .venv and installs all deps from pyproject.toml

# Run the app
uv run python src/main.py
```

`uv sync` reads `pyproject.toml` and locks dependencies into `.venv` automatically. No manual `pip install` needed.

---

## Environment Setup (pip — fallback)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/main.py
```

---

## API Key Setup

Create a `.env` file in the `ProficiencyTracker/` root:

```
GROQ_API_KEY=gsk_your_key_here
```

The app reads this automatically via `python-dotenv`. If the key is absent, capture and hero browsing work normally — only the HERO WIKI tab shows an error when you try to ask a question.

---

## CLAUDE.md and MCP

A `CLAUDE.md` file at the repo root gives Claude Code context about the project structure and conventions. It points to `specs/001-prof-tracker/plan.md` for detailed design notes.

MCP (Model Context Protocol) is not used in this project — the RAG pipeline uses the LlamaIndex + Groq stack directly. The Claude Code skills in `.claude/skills/` are development-time tools (spec writing, git workflow) used during the build process, not runtime components.

---

## First Run

On first launch when no hero data exists, ProfTracker opens a **First Run Setup** dialog that automatically downloads the live hero roster and icons from the Marvel Rivals Fandom wiki. This takes about 2–5 minutes depending on connection speed.

Click **Skip (use built-in roster)** to bypass the download and start with the 45-hero hardcoded roster immediately.

---

## Running Tests

```powershell
# With uv:
uv run pytest tests/

# With pip (.venv activated):
pytest tests/
```

Tests are split into `tests/unit/` (fast, no network) and `tests/integration/` (requires game window or fixture images).

---

## CI

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `.github/workflows/ci.yml` | Push or PR to `main` | Runs `pytest tests/unit/` on Windows |
| `.github/workflows/release.yml` | Push of a `v*` tag | Runs tests, builds PyInstaller exe, creates GitHub Release |

---

## PyInstaller Build (manual)

```powershell
pip install pyinstaller
pyinstaller proftracker.spec
# Output: dist/ProfTracker/ProfTracker.exe
```

The `.spec` file bundles Icons/, the app icon, and configures paths for the HuggingFace model cache.

---

## Index Storage

The RAG vector index lives at:
```
ProficiencyTracker/rag_index/
```
This folder is created automatically. Delete it (or click **Clear Index** in the app) to force a full rebuild.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Error: GROQ_API_KEY not set` | Create `.env` file with your key |
| First Run dialog hangs | Check internet connection; Fandom CDN required |
| OCR captures wrong values | Ensure game is at 1920×1080; try re-navigating to the Proficiency tab |
| `uv: command not found` | Run the uv installer first (see above), or use the pip fallback |
| HuggingFace download hangs | Check connection; model (~90 MB) downloads once to `~/.cache/huggingface/` |
