# Implementation Plan: ProfTracker — Marvel Rivals Hero Proficiency Tracker

**Branch**: `001-screen-data-capture` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)

---

## Summary

A Windows desktop application (Python + PyQt6) that lets the user select the Marvel Rivals game window by clicking it, then captures hero proficiency data one hero at a time via a hotkey session. The app grabs the game window directly with `PIL.ImageGrab`, reads the level via **EasyOCR** (handles the game's italic font) and the XP fraction via **pytesseract** from fixed pixel regions, validates every field, and stores results in a local SQLite database. A PyQt6 GUI provides window selection, session control, a real-time log, and a sidebar + detail hero browser after session completion. **No external APIs are used at runtime.**

---

## Technical Context

| Item                  | Decision                                                                         |
|-----------------------|----------------------------------------------------------------------------------|
| Language / Version    | Python 3.11+                                                                     |
| GUI                   | PyQt6 (≥6.6)                                                                     |
| OCR — level           | EasyOCR (neural net; handles the game's italic `LV##` font reliably)            |
| OCR — XP fraction     | pytesseract with `--psm 6` on a fixed pixel region                              |
| Image capture         | `PIL.ImageGrab.grab(bbox=win32gui.GetWindowRect(hwnd))` — direct screen grab    |
| Window selection      | PyQt6 transparent fullscreen overlay → `win32gui.WindowFromPoint(x, y)`         |
| In-game navigation    | User navigates manually; app is a compact always-on-top overlay during session  |
| Window management     | pywin32 (`win32gui.SetForegroundWindow`, `win32gui.IsWindow`)                   |
| Image preprocessing   | Greyscale conversion; EasyOCR receives raw 2× upscaled crop; pytesseract receives greyscale crop |
| Storage               | SQLite via Python built-in `sqlite3` (`proficiency_tracker.db`)                 |
| Testing               | pytest + pytest-qt                                                               |
| Platform              | Windows 10/11 only                                                               |
| External API calls    | None                                                                             |

---

## Constitution Check

| Principle                       | Gate                                                                              | Status |
|---------------------------------|-----------------------------------------------------------------------------------|--------|
| Hero Data Integrity             | Every Hero field validated before persistence; invalid records rejected atomically | ✅ PASS — FR-004; data-model.md validation rules |
| Progression Transparency        | Hero detail panel shows XP, level, progress bar; max-level heroes show "MAX"      | ✅ PASS — FR-007, FR-011; data-model.md progress formula |
| TDD (NON-NEGOTIABLE)            | Tests written and failing before any production code                              | ✅ PASS — tasks.md schedules tests first in each phase |
| Independent, Incremental Delivery | 4 user stories independently testable; each has its own checkpoint              | ✅ PASS — US1 (capture pipeline), US2 (window picker), US3 (storage), US4 (GUI) |
| Simplicity & Clarity First      | No external APIs; SQLite; clipboard capture per user spec; PyQt6 direct widget mapping | ✅ PASS — all dependencies justified in research.md |
| Local-Only Constraint           | No network calls at runtime; all OCR and storage is on-device                    | ✅ PASS — research.md §8 |

---

## Project Structure

### Documentation

```
specs/001-prof-tracker/
├── plan.md              ← this file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── storage-schema.sql
```

### Source Code

```
src/
├── main.py                    # Entry point; launches PyQt6 app + init DB
├── exceptions.py              # CaptureError, ParseError, ValidationError
├── models/
│   ├── hero.py                # Hero dataclass + field validation + progress_pct
│   └── capture_run.py         # CaptureRun dataclass + CaptureStatus enum
├── capture/
│   ├── window_picker.py       # Transparent QWidget overlay for window selection
│   ├── window.py              # Win32: is_window_alive, get_window_rect
│   ├── clipboard_capture.py   # capture_window() — direct PIL.ImageGrab screen grab
│   ├── navigator.py           # pyautogui: click_at, scroll_down, press_escape
│   ├── pipeline.py            # capture_one_hero() — grab screen, OCR, validate, store
│   ├── ocr.py                 # EasyOCR (level) + pytesseract (XP) — fixed pixel regions
│   └── debug.py               # save_debug_image() — writes timestamped PNGs to .temp/
├── data/
│   └── heroes.py              # HERO_ROSTER — known hero name list for dropdown
├── storage/
│   ├── database.py            # sqlite3 connection + schema init from DDL
│   └── repository.py          # HeroRepository.upsert, CaptureRunRepository CRUD
└── gui/
    ├── main_window.py         # QMainWindow: QStackedWidget scan panel <-> hero browser
    ├── scan_panel.py          # Session overlay: window picker, hotkey (2) capture, log
    ├── hero_browser.py        # QSplitter: QListWidget sidebar + HeroDetailPanel
    └── hero_detail.py         # Hero name, level, XP string, QProgressBar / MAX label

tests/
├── unit/
│   ├── test_hero_validation.py       # Hero field validation rules
│   ├── test_ocr_parser.py            # OCR parsing (pytesseract + EasyOCR mocked)
│   └── test_storage.py               # SQLite CRUD, upsert, cascade delete
└── integration/
    └── test_capture_pipeline.py      # run_scan() with mocked screen grab + OCR
```

---

## Implementation Phases

### Phase 1 — Models & Storage (US3)

**Goal**: Persist and retrieve Hero records; all other phases depend on this.

**Tasks** (test-first):
1. Write `tests/unit/test_hero_validation.py` — all Hero field rules; run → RED
2. Write `tests/unit/test_storage.py` — CRUD, upsert-by-name, cascade delete; run → RED
3. Implement `src/models/hero.py` (dataclass + `validate()`) → GREEN
4. Implement `src/models/capture_run.py` (dataclass + `CaptureStatus` enum) → GREEN
5. Implement `src/storage/database.py` (connect, `init_schema()` from DDL) → GREEN
6. Implement `src/storage/repository.py` (`HeroRepository.upsert`, `CaptureRunRepository`) → GREEN
7. All storage tests pass

**Checkpoint**: `pytest tests/unit/test_hero_validation.py tests/unit/test_storage.py` → all GREEN

---

### Phase 2 — Capture Pipeline (US1)

**Goal**: Clipboard capture → OCR → validated Hero records.

**Tasks** (test-first):
1. Write `tests/unit/test_ocr_parser.py` — parser edge cases (missing fields, bad values); run → RED
2. Write `tests/integration/test_capture_pipeline.py` — mock clipboard, assert Hero list returned; run → RED
3. Implement `src/capture/clipboard_capture.py`:
   - `focus_window(hwnd)` — `win32gui.SetForegroundWindow`
   - `capture_to_clipboard()` — `pyautogui.hotkey('alt', 'printscreen')`
   - `read_clipboard_image()` → `PIL.Image` via `PIL.ImageGrab.grabclipboard()`
   - `clear_clipboard()` — `win32clipboard.OpenClipboard → EmptyClipboard → CloseClipboard`
4. Implement `src/capture/ocr.py`:
   - `preprocess(image)` → greyscale → threshold → 2x upscale
   - `extract_heroes(image)` → list of raw dicts
   - `parse_hero(raw)` → `Hero` or raises `ParseError`
5. Implement `src/capture/window.py` (`validate_hwnd`, `is_window_alive`)
6. Implement `src/capture/navigator.py` (`scroll_hero_list`, `click_hero`)
7. All capture + OCR tests pass

**Checkpoint**: `pytest tests/unit/test_ocr_parser.py tests/integration/test_capture_pipeline.py` → all GREEN

---

### Phase 3 — Window Picker (US2)

**Goal**: User clicks the game window; app stores its HWND for the session.

**Tasks**:
1. Implement `src/capture/window_picker.py`:
   - `WindowPickerOverlay(QWidget)` — semi-transparent, always-on-top, cursor crosshair
   - `mousePressEvent` → resolve `win32gui.WindowFromPoint` → walk to top-level → emit `window_selected(hwnd, title)`
   - Close overlay on click or Escape
2. Manual test: overlay appears, click Marvel Rivals, HWND and title printed to console

**Checkpoint**: Window picker can be launched and returns a valid HWND

---

### Phase 4 — GUI (US4)

**Goal**: Full application UI with scan control, log, and hero browser.

**Tasks** (test-first for scan flow):
1. Implement `src/gui/scan_panel.py`:
   - "Select Window" button → launches `WindowPickerOverlay`
   - "Start Scan" button (disabled until window selected) → emits `scan_requested`
   - "Cancel" button (visible during scan) → emits `cancel_requested`
   - `QTextEdit` (read-only, auto-scroll) for log output
2. Implement scan worker (`QThread` subclass in `scan_panel.py`):
   - Runs capture pipeline; emits `log_message(str)`, `hero_captured(Hero)`, `scan_complete(int)`, `scan_failed(str)`
3. Implement `src/gui/hero_detail.py` (`HeroDetailPanel`):
   - Labels: name, role, level, XP string
   - `QProgressBar` (0–100) computed from `progress_pct`
   - "MAX" label shown when `is_max_level`
4. Implement `src/gui/hero_browser.py`:
   - `QSplitter`: left = `QListWidget` (hero names), right = `HeroDetailPanel`
   - Populates from repository after scan completes
5. Implement `src/gui/main_window.py`:
   - `QMainWindow` with `QStackedWidget`: scan panel ↔ hero browser
   - Transitions to hero browser when scan completes
6. Implement `src/main.py` (entry point: init DB, create `MainWindow`, exec app)
7. End-to-end manual test: select window → scan → browse heroes

**Checkpoint**: Full application runs; heroes visible in browser after a real or mock scan

---

## Key Design Decisions

### Capture Flow (per hero)
```
user presses 2 (or clicks "Capture Proficiency")
  → clipboard_capture.capture_window(hwnd)      # PIL.ImageGrab.grab(bbox=window_rect)
  → ocr._easyocr_level(image)                   # EasyOCR on _LEVEL_REGION (510,870,600,900)
  → pytesseract on image.crop(_XP_REGION)        # pytesseract on (450,910,630,970)
  → Hero validated + upserted to DB
  → result logged in UI
```

### OCR Strategy: Two-Engine Hybrid
The game's proficiency bar uses an italic font for the level number (`LV27`) that causes pytesseract to misread multi-digit values (e.g. confusing `LV1` and `LV11`). EasyOCR's neural-net approach handles this correctly.

- **Level** (`_LEVEL_REGION = (510, 870, 600, 900)`): EasyOCR, raw greyscale 2× upscale, with `_ocr_digits_str` look-alike substitution (italic A→4, S→5, I→1, etc.) applied to the full result string before matching.
- **XP fraction** (`_XP_REGION = (450, 910, 630, 970)`): pytesseract `--psm 6`, regex `\d+\s*/\s*\d+`, handles comma-separated large values and a `MAX` keyword for max-level heroes.

### Hero Upsert Strategy
Heroes are identified by name (unique). Each capture calls `HeroRepository.upsert(hero)`:
- If name exists → UPDATE all fields, update `capture_run_id` and `updated_at`
- If name not found → INSERT

This means the hero list always reflects the most recent capture, with no stale duplicates.

### Session UI Model
During a session the main window resizes to a compact 560×260 always-on-top overlay so it stays visible over the game. The user navigates in-game and presses **2** (polled via `win32api.GetAsyncKeyState`) to capture the current hero. On "Finish" the window restores to full size and the hero browser is shown.
