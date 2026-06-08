# ProfTracker v1.2 — Architecture Diagram

## Full System

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          ProfTracker v1.2 (PyQt6 Desktop App)                │
│                                                                              │
│  Nav: [ SCAN ] [ HEROES ] [ HERO WIKI ] [ TEAM-UPS ] [ TRAINING ]  [⟳ SYNC] │
│  ──────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SCAN tab    │  │ HEROES tab  │  │  TEAM-UPS    │  │  TRAINING tab    │  │
│  │ (ScanPanel)  │  │(HeroBrowser)│  │    tab       │  │ (TrainingPanel)  │  │
│  │              │  │             │  │(TeamUpsPanel)│  │                  │  │
│  │ OCR Pipeline │  │ Hero cards  │  │ Synergy list │  │ Per-hero drills  │  │
│  │ ┌──────────┐ │  │ XP progress │  │ from wiki    │  │ from ability data│  │
│  │ │EasyOCR   │ │  │ bars        │  └──────────────┘  └──────────────────┘  │
│  │ │pytesseract│ │  │             │                                          │
│  │ └────┬─────┘ │  │             │  ┌───────────────────────────────────┐   │
│  │      │       │  │             │  │         HERO WIKI tab             │   │
│  │  SQLite DB   │  │             │  │        (HeroInfoPanel)            │   │
│  │ ┌──────────┐ │  │             │  │                                   │   │
│  │ │ heroes   │ │  │             │  │  [URL Input          ] [Add]      │   │
│  │ │ capture_ │ │  │             │  │  Status: N chunks indexed  [Clear]│   │
│  │ │  runs    │ │  │             │  │  Chat history (QTextBrowser)      │   │
│  │ │snapshots │ │  │             │  │  [Ask a question...   ] [Ask]     │   │
│  │ └──────────┘ │  └─────────────┘  └──────────────┬────────────────────┘  │
│  └──────────────┘                                  │                        │
│                                                    │                        │
│  ┌─────────────────────────────────────────────────┼────────────────────┐   │
│  │              SYNC panel  (SyncPanel)            │                    │   │
│  │  [SYNC FROM WIKI]  Progress bar  Scrollable log │                    │   │
│  └─────────────────────────────────────────────────┼────────────────────┘   │
└────────────────────────────────────────────────────┼────────────────────────┘
                                                     │
                     ┌───────────────────────────────┼───────────────────────┐
                     │         Async Layer (QThread workers)                 │
                     │                               │                       │
                     │  ┌─────────────┐  ┌───────────┴──────┐  ┌──────────┐ │
                     │  │ IngestWorker│  │  QueryWorker     │  │SyncWorker│ │
                     │  │ (QThread)   │  │  (QThread)       │  │(QThread) │ │
                     │  └──────┬──────┘  └────────┬─────────┘  └────┬─────┘ │
                     │         │                  │                  │       │
                     │         ▼                  ▼                  ▼       │
                     │  ┌─────────────┐  ┌────────────────┐  ┌────────────┐ │
                     │  │MediaWiki API│  │VectorIndex     │  │avatar_sync │ │
                     │  │+ BeautifulS │  │Retriever top-3 │  │ability_    │ │
                     │  │  oup        │  └────────┬───────┘  │  scraper   │ │
                     │  └──────┬──────┘           │          └────┬───────┘ │
                     │         │                  ▼               │         │
                     │         ▼         ┌────────────────┐       │         │
                     │  ┌─────────────┐  │  Groq API      │       │         │
                     │  │HuggingFace  │  │  llama-3.3-70b │  Icons/ + heroes│
                     │  │bge-small    │  └────────┬───────┘  .json + abilities│
                     │  │(local embed)│           │               │         │
                     │  └──────┬──────┘    Answer + Sources       │         │
                     │         ▼                                  ▼         │
                     │  ┌──────────────────────────┐   ┌────────────────┐   │
                     │  │  VectorStoreIndex        │   │ rebuild_index()│   │
                     │  │  (LlamaIndex in-memory)  │──▶│ bulk ingest    │   │
                     │  │  rag_index/ (disk)        │   │ 50+ hero URLs  │   │
                     │  └──────────────────────────┘   └────────────────┘   │
                     └───────────────────────────────────────────────────────┘

First Run (no hero data):
  app launch → FirstRunDialog → SyncWorker → heroes.json + Icons/ + RAG index
                             ↕ user can skip
                        built-in heroes.py roster
```

---

## Data Flow — Wiki Auto-Sync

```
User clicks "SYNC FROM WIKI"  (or FirstRunDialog auto-starts)
         │
         ▼ SyncWorker (background QThread)
         │
         ├──▶ avatar_sync.parse_avatars_page()
         │         │  Fandom wiki "Avatars" page → list of hero icon sets
         │         │  each set: hero name, wiki_page slug, icon URLs
         │         ▼
         │    sync_icons()  →  download Hero/Lord/Champion .webp files
         │                     skip files already present in Icons/
         │         │
         │         ▼
         │    write_heroes_py()  →  write heroes.json from live roster
         │
         ├──▶ ability_scraper.sync_abilities()
         │         │  one MediaWiki API call per hero
         │         │  stores structured ability text in hero_data/
         │         ▼
         │    scrape_teamups()  →  team-up synergy data → hero_data/
         │
         └──▶ rag.ingest.rebuild_index(hero_urls)
                   │  bulk ingest all 50+ hero wiki pages
                   │  same MediaWiki API + bge-small pipeline as manual ingest
                   ▼
              rag_index/ (fully rebuilt)
         │
         ▼ finished signal → UI: summary line + sync_complete signal
              → MainWindow reloads hero browser + team-ups panel
```

---

## Data Flow — OCR Capture

```
User presses hotkey (2) during a session
         │
         ▼ (main thread — ScanPanel)
window.capture_region(hero_level_bbox)
window.capture_region(xp_bbox)
         │
         ▼ EasyOCR + pytesseract
         │  parse digits → (level: int, xp: int)
         │  validate: level in [1..MAX], xp in [0..xp_table[level]]
         ▼
HeroRepository.upsert(hero_name, level, xp)  → SQLite
         │
         ▼ Activity log appends: "✓ Iron Man — Lv 15, 4200 XP"
```

---

## Data Flow — RAG Query

```
User types question → presses Ask
         │
         ▼ QueryWorker (background QThread)
         │
VectorIndexRetriever.retrieve(query)
  cosine similarity, top-k=3
         │
         ▼ ResponseSynthesizer (compact mode)
  system prompt + retrieved chunks + user query
         │
         ▼ Groq API — llama-3.3-70b-versatile (temperature=0.1)
         │
         ▼ Answer text + source URLs → HeroInfoPanel chat display
```

---

## Component Map

| Component | File | Responsibility |
|-----------|------|---------------|
| MainWindow | `src/gui/main_window.py` | Tab navigation, update banner, wires all panels |
| ScanPanel | `src/gui/scan_panel.py` | OCR session UI, hotkey handler, activity log |
| HeroBrowser | `src/gui/hero_browser.py` | Scrollable hero roster + detail cards |
| HeroInfoPanel | `src/gui/hero_info_panel.py` | HERO WIKI tab: URL input, chat display |
| TeamUpsPanel | `src/gui/teamups_panel.py` | TEAM-UPS tab: synergy display |
| TrainingPanel | `src/gui/training_panel.py` | TRAINING tab: per-hero drills |
| SyncPanel | `src/gui/sync_panel.py` | SYNC panel: trigger + progress log |
| FirstRunDialog | `src/gui/first_run_dialog.py` | First-launch setup dialog (HITL: skip button) |
| SyncWorker | `src/wiki_sync/worker.py` | QThread: icons + abilities + team-ups + RAG rebuild |
| avatar_sync | `src/wiki_sync/avatar_sync.py` | Fandom icon scraping + heroes.json writer |
| ability_scraper | `src/wiki_sync/ability_scraper.py` | Hero ability + team-up data scraping |
| IngestWorker | `src/rag/worker.py` | QThread: scrape URL + embed + persist |
| QueryWorker | `src/rag/worker.py` | QThread: retrieve + generate answer |
| ingest.py | `src/rag/ingest.py` | Index lifecycle: build, load, insert, clear, rebuild |
| query_engine.py | `src/rag/query_engine.py` | Retriever + synthesizer factory |
| Database | `src/storage/database.py` | SQLite connection + schema init |
| HeroRepository | `src/storage/repository.py` | Hero CRUD; snapshot backfill |

---

## Key Design Decisions

**Why QThread throughout?**
ProfTracker's codebase is synchronous PyQt6. Every network or compute-heavy operation (OCR, wiki scraping, embedding, Groq call) runs in a QThread worker so the UI never freezes. The consistent `progress(int, int, str)` / `finished` / `error` signal contract means all async operations drive the same progress bar + log pattern.

**Why bge-small-en-v1.5 for embeddings?**
Runs fully locally (no API cost per embed), downloads once to `~/.cache/huggingface/` (~90 MB), and scores competitively with larger models on English retrieval benchmarks.

**Why MediaWiki API instead of direct HTML scraping?**
Fandom pages require JavaScript rendering that BeautifulSoup cannot execute. The MediaWiki `action=parse` endpoint returns fully-rendered HTML server-side; the `action=query&prop=revisions` endpoint returns raw wikitext. Both work without a headless browser and without hitting Cloudflare bot detection.

**Why two documents per URL during ingest?**
Hero stat tables (role, HP, difficulty) produce embeddings diluted by lore text when chunked together. Isolating them into a compact "stats document" ensures stat queries retrieve the correct chunk at rank 1 rather than being outranked by ability descriptions that happen to mention numbers.

**Why `%APPDATA%` for the database?**
Storing `proficiency_tracker.db` inside the install directory means a PyInstaller update wipes it. Moving to `%APPDATA%\ProficiencyTracker\` decouples user data from app updates (resolved in v1.0.6).
