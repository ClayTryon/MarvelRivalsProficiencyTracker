# Sprint 4 (Week 8) — Deliverables Index
**Course:** AI 410 | **Student:** Clay Tryon | **Date:** June 2026

---

## What Was Added This Sprint

### New Source Files (in `src/`)
| File | Purpose |
|------|---------|
| `src/wiki_sync/__init__.py` | Package marker |
| `src/wiki_sync/avatar_sync.py` | Scrapes Fandom Avatars page; downloads Hero/Lord/Champion icons; writes `heroes.json` |
| `src/wiki_sync/ability_scraper.py` | Fetches hero ability text and team-up synergy data from the wiki |
| `src/wiki_sync/worker.py` | `SyncWorker` QThread: orchestrates icons → abilities → team-ups → RAG rebuild |
| `src/gui/first_run_dialog.py` | First Run dialog shown on first launch; runs `SyncWorker` automatically with a Skip option |
| `src/gui/sync_panel.py` | SYNC tab panel: trigger button, progress bar, scrollable log |
| `src/gui/teamups_panel.py` | TEAM-UPS tab: displays hero synergy data |
| `src/gui/training_panel.py` | TRAINING tab: per-hero training recommendations |
| `src/gui/abilities_panel.py` | Per-hero ability detail panel |

### Modified Files
| File | Change |
|------|--------|
| `src/gui/main_window.py` | Added TEAM-UPS (`_TAB_TEAMUPS = 3`), TRAINING (`_TAB_TRAINING = 4`), SYNC (`_TAB_SYNC = 5`) panels; added ⟳ SYNC button to nav bar; wired `sync_complete` → hero browser + team-ups reload |
| `src/main.py` | Added first-run check: if no heroes in DB, opens `FirstRunDialog` then seeds defaults |
| `src/rag/ingest.py` | Added `rebuild_index(urls, progress_cb)` for bulk ingest during wiki sync |
| `.github/workflows/release.yml` | Added `pytest tests/unit/` step before PyInstaller build |
| `.github/workflows/ci.yml` | **New** — runs `pytest tests/unit/` on every push and PR to `main` |
| `pyproject.toml` | **New** — `uv`-compatible project manifest with all dependencies |

---

## Week 8 Deliverables (this folder)

| File | Contents |
|------|---------|
| `SPEC.md` | Finalized specification v0.5: FR-001–FR-027, NFR, HITL design, observability design |
| `architecture.md` | Updated full system diagram for v1.2 including wiki sync, first-run flow, all new tabs |
| `setup_notes.md` | Environment setup with uv, pip fallback, CLAUDE.md/MCP notes, CI table, troubleshooting |
| `risk_register.md` | 8 active risks with likelihood/impact/mitigation/Week 9 action; 4 closed risks |
| `demo_evidence.md` | OCR capture log, wiki sync log, RAG eval results, live RAG transcript, UI screenshot table |
| `HeroPage.png` | Screenshot — HEROES tab with hero roster |
| `HeroAbilities.png` | Screenshot — Hero ability detail panel |
| `HeroWiki.png` | Screenshot — HERO WIKI tab with RAG chat answer |
| `HeroSync.png` | Screenshot — SYNC panel running wiki sync |
| `FirstTimeSetup.png` | Screenshot — First Run dialog (first-launch HITL checkpoint) |
| `README.md` | This file — sprint index |

---

## Quick Start

```powershell
# Install uv, then:
uv sync
uv run python src/main.py
```

See `setup_notes.md` for full instructions including pip fallback, API key, and CI details.
