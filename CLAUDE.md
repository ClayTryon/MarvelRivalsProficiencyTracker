# ProfTracker — Claude Code Context

## Project

Windows desktop app (PyQt6) for Marvel Rivals players. Tracks hero proficiency via OCR screen capture, provides a wiki RAG chat (Groq + LlamaIndex), and syncs the hero roster and icons from an AWS S3 CDN (updated daily by an EC2 scraper).

Current version: 1.2.3

## Structure

```
src/
  main.py              — entry point; DPI setup, DB init, first-run dialog
  capture/             — OCR pipeline (EasyOCR, Interception driver, fixed pixel regions)
  gui/                 — all PyQt6 panels; QThread workers in rag/ and wiki_sync/
  rag/                 — LlamaIndex RAG: ingest.py, query_engine.py, worker.py
  wiki_sync/           — CDN + wiki sync: avatar_sync.py, ability_scraper.py, worker.py
  storage/             — SQLite via database.py + repository.py
  data/                — heroes.py roster, xp_table.py, proficiency_missions.py
  models/              — Hero and CaptureRun dataclasses
tests/
  unit/                — pytest unit tests (mocked OCR, storage, ability scraper)
  integration/         — integration test for capture pipeline guard
```

## Run

```powershell
uv sync --extra dev
uv run python src/main.py
uv run pytest tests/unit/
```

## Key conventions

- All async work runs in QThread workers with `progress(int, int, str)` / `finished` / `error` signals
- Database lives in `%APPDATA%\ProficiencyTracker\` (not the install dir)
- `GROQ_API_KEY` is embedded in `src/api_keys.py` (XOR obfuscated); `.env` override is supported but not required
- `CDN_BASE` is hardcoded in `wiki_sync/avatar_sync.py` — no env var needed for CDN sync
- `heroes.json` is downloaded from S3 on first run and takes precedence over the hardcoded `heroes.py` list
- `is_synced()` in `data/heroes.py` gates the Auto Scan feature — scan won't run until heroes.json exists
- Icon naming: `Hero_Icon_{slug}.webp`, `Lord_Icon_{slug}.webp`, `Champion_Icon_{slug}_Animated.gif`
- Frozen exe (PyInstaller): paths use `sys._MEIPASS`; spec is `proftracker.spec`

## CDN Architecture

Hero data (icons, abilities, heroes.json) is served from S3 (`proftracker-wiki-data-clayhtryon.s3.amazonaws.com`). An EC2 t3.micro instance scrapes the Fandom wiki daily via EventBridge and uploads to S3. Clients always sync from CDN — direct wiki scraping is a fallback path only.

## Known Limitations

- Windows 10/11 only (Interception driver + win32 APIs)
- English language only (OCR allowlists, UI, wiki data)
- Auto Scan calibrated for 1920×1080 windowed mode
- Level 1 hero XP tracking is inherently imprecise (OCR reads small regions at low level values)
