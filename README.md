# ProficiencyTracker for Marvel Rivals

Automatically scans and tracks hero proficiency levels across sessions, with XP progression charts and data export.

---

## Requirements

- **Windows 10/11**
- **Marvel Rivals** installed and running
- **Interception driver** — required for Auto Scan only
  - Download: https://github.com/oblitum/Interception
  - Extract the zip to your **C: drive** (e.g. `C:\Interception`) — the installer will not work from other drives
  - Open an **Administrator Command Prompt** and run:
    ```
    cd "C:\Interception\command line installer"
    install-interception.exe /install
    ```
  - Reboot your PC after installation

OCR is built into the app — no separate install needed.

---

## Installation

1. Download `ProfTracker-windows.zip` from the [latest release](../../releases/latest)
2. Extract the zip anywhere on your computer
3. Run `ProfTracker.exe`

Your hero data is saved to `%APPDATA%\ProficiencyTracker\` and is preserved across updates.

---

## Usage

### Auto Scan

Auto Scan drives the game automatically and captures every hero in one pass.

**Before using Auto Scan:**
- Install the Interception driver (see Requirements above)
- Make sure Marvel Rivals is open on the Heroes grid screen
- Display Mode: **Windowed**, Resolution: **1920 × 1080**

**Steps:**
1. Select the game window using **Select Window**
2. Click **Auto Scan**
3. When prompted, **move your mouse once** then **press any key** — this registers your input devices
4. Switch to the Marvel Rivals window within 4 seconds
5. ProfTracker will navigate and capture all heroes automatically
6. Press **Backspace** at any time to cancel mid-scan

### Clipboard Scan

Update a single hero without the Interception driver:

1. In-game, navigate to the hero's **Proficiency** tab
2. Press **Alt+PrintScreen** to copy the game window to your clipboard
3. In ProfTracker, go to **HEROES**, right-click the hero's card, and choose **Scan from Clipboard**

### Viewing Results

- The **HEROES** tab shows all captured heroes with level, XP, and a progress bar
- Click a hero card to open the detail panel with XP history chart and velocity estimate
- The **TRAINING** tab spins a random hero that hasn't earned Lord (LV20) yet — filter by role
- Use the **⋯** menu in HEROES to export to Excel or import from a filled-in template

---

## Antivirus Warning

Some antivirus tools may flag `ProfTracker.exe` with detections such as:

- `Riskware.PyInstaller` (Yandex)
- `W32.Malware.7097E53A` (Bkav Pro)
- `Malicious` (SecureAge)

**These are false positives.** ProfTracker is packaged with PyInstaller, a standard Python bundling tool. Several antivirus engines flag all PyInstaller executables by default due to the packaging method, not because of any malicious code. The source code is fully available in this repository for review.

If your antivirus blocks the app, add `ProfTracker.exe` to its exclusion list.

---

## Data & Privacy

ProfTracker does not connect to the internet (except for update checks and Hero Wiki queries). All hero data is stored locally at:

```
%APPDATA%\ProficiencyTracker\proficiency_tracker.db
```

---

## Known Limitations

- **Windows only.** The Interception kernel driver and `ctypes` DPI/focus APIs are Windows-specific. Auto Scan will not run on macOS or Linux.
- **1920×1080 required for Auto Scan.** OCR reads from fixed fractional pixel regions calibrated to 1080p. Other resolutions produce incorrect crops.
- **Interception driver required for Auto Scan.** Clipboard Scan works without it for single-hero updates.
- **RAG requires a GROQ_API_KEY.** Without it the Hero Wiki tab loads but returns an error on every query. The rest of the app is unaffected.
- **Hero roster is locked to heroes.json.** If a new hero is released before a wiki sync, the scanner will not recognize them. Run a sync after each game patch.
- **OCR accuracy degrades on non-standard fonts or UI mods.** ProfTracker is calibrated against the default Marvel Rivals UI theme.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  ProfTracker Desktop (PyQt6)                                │
│                                                             │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ ScanPanel│ │HeroBrows│ │ HeroWiki │ │  SyncPanel    │  │
│  │          │ │   er    │ │ (RAG)    │ │               │  │
│  └────┬─────┘ └────┬────┘ └────┬─────┘ └──────┬────────┘  │
│       │             │           │               │           │
│  ┌────▼─────────────▼──┐  ┌────▼─────┐  ┌──────▼────────┐  │
│  │  OCR Pipeline       │  │ RAG      │  │ Wiki Sync     │  │
│  │  EasyOCR + Intercept│  │ LlamaIdx │  │ Fandom API    │  │
│  │  ion driver         │  │ + Groq   │  │ + avatar/abil │  │
│  └────────────┬────────┘  └────┬─────┘  └──────┬────────┘  │
│               │                │                │           │
│  ┌────────────▼────────────────▼────────────────▼────────┐  │
│  │  SQLite  (WAL mode)  +  heroes.json  +  rag_index/    │  │
│  │  %APPDATA%\ProficiencyTracker\                        │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data flow — OCR scan:** Game window (Interception driver) → screenshots → EasyOCR → level/XP → SQLite hero + hero_snapshot tables.

**Data flow — RAG query:** User question → LlamaIndex VectorStoreIndex (BAAI/bge-small-en-v1.5 embeddings) → top-k chunks → Groq llama-3.3-70b → answer.

**Data flow — wiki sync:** AWS S3 CDN (updated daily by EC2 scraper) → heroes.json + icons + ability JSON → local disk → SQLite seeded. Falls back to direct Fandom MediaWiki API scraping if CDN is unavailable.

---

## Developer Setup

**Prerequisites:** [uv](https://github.com/astral-sh/uv) (Python package manager), Python 3.11+, Windows 10/11.

```powershell
# Install dependencies (including dev extras)
uv sync --extra dev

# Run the app from source
uv run python src/main.py

# Run unit tests
uv run pytest tests/unit/ -v

# Run a specific test file
uv run pytest tests/unit/test_ocr_parser.py -v
```

**Environment variables** (optional — create a `.env` file in the project root to override defaults):

```
GROQ_API_KEY=your_groq_api_key_here  # embedded by default; override here if needed
```

**Build a standalone executable:**

```powershell
uv run pyinstaller ProfTracker.spec
# Output: dist/ProfTracker/ProfTracker.exe
```

**Project structure:**

```
src/
  main.py              — entry point; DPI setup, DB init, first-run dialog
  capture/             — OCR pipeline (EasyOCR, Interception driver)
  gui/                 — PyQt6 panels; QThread workers in rag/ and wiki_sync/
  rag/                 — LlamaIndex RAG: ingest, query engine, QueryWorker
  wiki_sync/           — CDN + wiki sync: avatars, abilities, SyncWorker
  storage/             — SQLite database.py + repository.py
  data/                — heroes.py roster, xp_table.py, proficiency_missions.py
  models/              — Hero dataclass, CaptureRun dataclass
tests/
  unit/                — pytest unit tests (mocked OCR, storage, scraper)
```
