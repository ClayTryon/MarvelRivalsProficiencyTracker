# Tasks: ProfTracker — Marvel Rivals Hero Proficiency Tracker

**Branch**: `001-screen-data-capture` | **Date**: 2026-04-18
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

---

## Screen & OCR Reference

Based on `Tasks examples.docx` and live testing at 1920×1080:

- **Proficiency page bottom bar**: Contains all target data. Format:
  ```
  [HERO NAME]    LV[N]
  PROFICIENCY  [icon]  [current_xp] /[required_xp]
  [progress bar]
  ```
  Example: `CAPTAIN  LV11` / `PROFICIENCY  44 /400`
  Large XP example: current_xp = `2452081`, required_xp = `3000000`
  Max-level heroes show `0 /0` or a `MAX` indicator.

- **OCR pixel regions (1920×1080 screenshot coords, origin top-left of window):**

  | Field      | Region (left, top, right, bottom) | Engine      | Notes |
  |------------|-----------------------------------|-------------|-------|
  | Level      | `(510, 870, 600, 900)`            | EasyOCR     | Italic font; pytesseract misreads multi-digit values. `_ocr_digits_str` substitution applied (A→4, S→5, I→1, etc.). |
  | XP fraction| `(450, 910, 630, 970)`            | pytesseract | `--psm 6`; regex `\d+\s*/\s*\d+`; handles commas and `MAX` keyword. |

- **Debug images**: Every capture writes timestamped PNGs to `.temp/` via `save_debug_image()`:
  - `proficiency_raw` — full screen grab
  - `proficiency_xp_crop` — pytesseract input for XP
  - `level_ocr_input` — EasyOCR input for level (greyscale, 2× upscale)

---

## Phase 0 — Debug Image Saving (Temporary)

### T-000 · Implement .temp debug image saving
**Type**: implementation | **Depends on**: none

> **TEMPORARY** — exists only for debugging the capture pipeline. Remove once OCR is verified working.

Create `src/capture/debug.py`:

```python
import os
from datetime import datetime
from PIL import Image

TEMP_DIR = ".temp"

def save_debug_image(image: Image.Image, label: str) -> str:
    """Save image to .temp/ with a timestamp+label filename. Returns the saved path."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%H%M%S_%f")
    filename = f"{timestamp}_{label}.png"
    path = os.path.join(TEMP_DIR, filename)
    image.save(path)
    return path
```

Call `save_debug_image(image, label)` immediately after every `read_clipboard_image()` call in the pipeline, and after every crop/preprocess step. Labels to use:

| Call site | Label |
|-----------|-------|
| After main menu grab | `"01_main_menu"` |
| After heroes grid grab | `"02_heroes_grid"` |
| After hero card crop | `"03_card_{index}"` |
| After hero overview grab | `"04_hero_overview_{name}"` |
| After proficiency page grab | `"05_proficiency_{name}"` |
| After preprocessing (OCR input) | `"06_ocr_input_{name}"` |

Add `.temp/` to `.gitignore`.

The `.temp/` folder is **not cleared between runs** so you can compare grabs across attempts. Clear it manually when done debugging.

---

## Phase 1 — Models & Storage

### T-001 · Write Hero validation tests
**Type**: test | **Depends on**: none

Write `tests/unit/test_hero_validation.py`. Tests must be RED before any model code is written.

Cover:
- Valid Hero passes validation (name, role, level ≥ 1, xp ≥ 0, xp_required ≥ 0)
- Empty name raises `ValidationError`
- `level < 1` raises `ValidationError`
- `xp < 0` raises `ValidationError`
- `is_max_level=True` with `xp_required > 0` raises `ValidationError`
- `xp >= xp_required` when `is_max_level=False` raises `ValidationError`
- `progress_pct` returns 0.0 when `is_max_level=True`
- `progress_pct` returns correct float when `is_max_level=False`

---

### T-002 · Write storage tests
**Type**: test | **Depends on**: none

Write `tests/unit/test_storage.py`. Tests must be RED before storage code is written.

Cover:
- `init_schema()` creates `hero` and `capture_run` tables
- `CaptureRunRepository.create()` inserts and returns a `CaptureRun`
- `CaptureRunRepository.update_status()` changes status and sets `completed_at`
- `HeroRepository.upsert()` inserts a new hero
- `HeroRepository.upsert()` updates an existing hero (same name, different level/xp)
- `HeroRepository.get_all()` returns all heroes ordered by name
- Deleting a `CaptureRun` cascades and removes its linked heroes

---

### T-003 · Implement Hero model
**Type**: implementation | **Depends on**: T-001

Create `src/models/hero.py`:
- `@dataclass Hero` with fields: `name`, `role`, `level`, `xp`, `xp_required`, `is_max_level`, `capture_run_id`, `updated_at`
- `validate()` method — raises `ValidationError` on any rule failure
- `progress_pct` property — returns `float` (0.0–100.0)

Create `src/exceptions.py` with `ValidationError` and `ParseError`.

Run T-001 → must be GREEN.

---

### T-004 · Implement CaptureRun model
**Type**: implementation | **Depends on**: T-002

Create `src/models/capture_run.py`:
- `CaptureStatus` enum: `RUNNING`, `COMPLETED`, `CANCELLED`, `FAILED`
- `@dataclass CaptureRun` with fields matching the storage schema

---

### T-005 · Implement database + repository
**Type**: implementation | **Depends on**: T-003, T-004

Create `src/storage/database.py`:
- `Database(db_path: str)` class
- `connect()` — opens SQLite connection, enables `PRAGMA foreign_keys = ON`
- `init_schema()` — executes DDL from `specs/001-prof-tracker/contracts/storage-schema.sql`

Create `src/storage/repository.py`:
- `CaptureRunRepository` — `create()`, `update_status()`, `get_latest()`
- `HeroRepository` — `upsert(hero: Hero)` (INSERT OR REPLACE by name), `get_all()`, `get_by_name(name)`

Run T-002 → must be GREEN.

---

## Phase 2 — Capture Pipeline

### T-006 · Write OCR parser tests
**Type**: test | **Depends on**: T-003

Write `tests/unit/test_ocr_parser.py`. Tests must be RED before OCR code is written.

Cover (use synthetic/saved test images or text strings — no live game required):
- `parse_hero_card_name(image)` returns `"ADAM WARLOCK"` from a hero grid card snip
- `parse_proficiency_bar(image)` returns `("CAPTAIN", 11, 44, 400, False)` from a proficiency bar snip
- `parse_proficiency_bar` handles large XP values (`2452081`, `121854`)
- `parse_proficiency_bar` raises `ParseError` when "PROFICIENCY" text not found
- `parse_proficiency_bar` sets `is_max_level=True` when required_xp is 0 or "MAX" detected
- `detect_text_in_region(image, keyword)` returns True when keyword present (case-insensitive)

Save reference test images to `tests/fixtures/` (crop from docx screenshots or create synthetic ones).

---

### T-007 · Write capture pipeline integration test
**Type**: test | **Depends on**: T-006

Write `tests/integration/test_capture_pipeline.py`.

Mock `clipboard_capture.read_clipboard_image()` to return a saved test image.
Assert that `run_capture_pipeline(hwnd, db)` returns a list of `Hero` objects with correct fields.
Tests must be RED.

---

### T-008 · Implement clipboard capture
**Type**: implementation | **Depends on**: T-007

Create `src/capture/clipboard_capture.py`:

```python
def focus_window(hwnd: int) -> None
    # Brings hwnd to foreground via thread-input attachment

def capture_window(hwnd: int) -> PIL.Image.Image
    # win32gui.GetWindowRect(hwnd) → PIL.ImageGrab.grab(bbox=rect, all_screens=True)
    # raises CaptureError if rect is (0,0,0,0) or grab returns None
```

Direct screen grab — no clipboard involved. Avoids timing issues and clipboard conflicts.

---

### T-009 · Implement OCR module
**Type**: implementation | **Depends on**: T-006

Create `src/capture/ocr.py`:

- `preprocess(image: PIL.Image) -> PIL.Image`
  - Convert to greyscale (used by pytesseract paths)

- `detect_text_in_region(image, keyword, region=None) -> bool`
  - Optionally crop `image` to `region` tuple `(left, top, right, bottom)`
  - Run `pytesseract.image_to_string()` on greyscale crop
  - Return `keyword.lower() in result.lower()`

- `parse_hero_card_name(image: PIL.Image) -> str`
  - Crop bottom 20% of the image (the dark name banner)
  - pytesseract with `--psm 7` (single line)
  - Return cleaned uppercase string

- `_easyocr_level(image: PIL.Image) -> int`
  - Crop `_LEVEL_REGION = (510, 870, 600, 900)`
  - Raw greyscale, 2× upscale, pass to EasyOCR
  - Apply `_ocr_digits_str` substitution (italic look-alikes: A→4, S→5, I→1, L→1, etc.)
  - Match `1V\s*([\d\s]+)` (LV→1V after substitution); strip spaces; return int
  - Raises `ParseError` if level cannot be extracted

- `parse_proficiency_bar(image: PIL.Image) -> tuple[str, int, int, int, bool]`
  - Calls `_easyocr_level(image)` for the level
  - Crops `_XP_REGION = (450, 910, 630, 970)` for XP; pytesseract `--psm 6`
  - Checks for `MAX` keyword → returns `("", level, 0, 0, True)`
  - Parses `\d+ / \d+` pattern for `(xp, xp_required)`; `is_max = xp_required == 0`
  - Raises `ParseError` if XP pattern not matched

Run T-006 → must be GREEN.

---

### T-010 · Implement window module
**Type**: implementation | **Depends on**: none

Create `src/capture/window.py`:

- `is_window_alive(hwnd: int) -> bool` — `win32gui.IsWindow(hwnd)`
- `get_window_title(hwnd: int) -> str` — `win32gui.GetWindowText(hwnd)`
- `get_window_rect(hwnd: int) -> tuple[int,int,int,int]` — `win32gui.GetWindowRect(hwnd)`

---

### T-011 · Implement navigator
**Type**: implementation | **Depends on**: T-010

Create `src/capture/navigator.py`:

- `click_at(hwnd, rel_x_pct, rel_y_pct, delay=0.5)` — compute absolute coords from window rect + relative percentages, `pyautogui.click`, sleep
- `scroll_down(hwnd, amount=3)` — `pyautogui.scroll(-amount)` at window center
- `press_escape()` — `pyautogui.press('escape')`

All coordinates computed from `get_window_rect` so they work at any screen resolution.

---

### T-012 · Implement full capture pipeline
**Type**: implementation | **Depends on**: T-008, T-009, T-011

Create `src/capture/pipeline.py` with `run_scan(hwnd, db, on_log, on_hero, check_cancelled)`:

```
1. Validate hwnd is alive → raise CaptureError if not
2. focus_window(hwnd)
3. capture_to_clipboard() → read → clear
4. detect_text_in_region(image, 'play', top_left_quadrant)
   → if False: raise CaptureError("Game is not on the main menu")
5. Store image resolution for coordinate scaling
6. Locate and click 'HEROES' nav button (relative coords based on resolution)
7. sleep(1.0) — wait for heroes grid to load
8. Loop:
   a. capture_to_clipboard() → read → clear
   b. Count visible hero cards (detect grid, expect up to 14)
   c. For each card (index 0–13):
      i.   Crop card region from grid image
      ii.  name = parse_hero_card_name(card_crop)
      iii. click_at(hwnd, card_center_x_pct, card_center_y_pct)
      iv.  sleep(0.5)
      v.   capture_to_clipboard() → read → clear
      vi.  detect_text_in_region(image, 'proficiency') → click PROFICIENCY tab
      vii. sleep(0.5)
      viii.capture_to_clipboard() → read → clear
      ix.  (name2, level, xp, xp_req, is_max) = parse_proficiency_bar(image)
      x.   Validate + upsert Hero to DB
      xi.  on_hero(hero); on_log(f"Captured {name2} LV{level}")
      xii. press_escape() → sleep(0.5)
      xiii.if check_cancelled(): return
   d. If card count == 14: scroll_down → sleep(1.0) → continue loop
   e. If card count < 14: break (last page)
9. Return hero_count
```

Run T-007 → must be GREEN.

---

## Phase 3 — Window Picker

### T-013 · Implement window picker overlay
**Type**: implementation | **Depends on**: none (pure Qt + win32)

Create `src/capture/window_picker.py`:

- `WindowPickerOverlay(QWidget)`:
  - Fullscreen, always-on-top, semi-transparent (alpha 80/255), cursor set to crosshair
  - Label at top: "Click the Marvel Rivals window to select it. Press Escape to cancel."
  - `mousePressEvent`: get click position → `win32gui.WindowFromPoint(x, y)` → walk parent chain to top-level → emit `window_selected(hwnd: int, title: str)` → close
  - `keyPressEvent`: Escape → emit `cancelled()` → close

- `pick_window(parent=None) -> tuple[int, str] | None`
  - Shows overlay, runs event loop, returns `(hwnd, title)` or `None` if cancelled

---

## Phase 4 — GUI

### T-014 · Implement HeroDetailPanel
**Type**: implementation | **Depends on**: T-003

Create `src/gui/hero_detail.py`:

- `HeroDetailPanel(QWidget)`:
  - Labels: hero name (large), role, level string (e.g. "Level 11")
  - XP string: "44 / 400 XP"
  - `QProgressBar` (0–100), value = `hero.progress_pct`
  - When `is_max_level`: hide progress bar, show "MAX LEVEL" label in gold
  - `set_hero(hero: Hero)` method to update all fields

---

### T-015 · Implement HeroBrowser
**Type**: implementation | **Depends on**: T-014, T-005

Create `src/gui/hero_browser.py`:

- `HeroBrowser(QWidget)`:
  - `QSplitter` (horizontal): left = `QListWidget` (hero names, sorted A–Z), right = `HeroDetailPanel`
  - `load_heroes(heroes: list[Hero])` — populates list, selects first item
  - `QListWidget.currentRowChanged` → update `HeroDetailPanel` with selected hero

---

### T-016 · Implement ScanPanel
**Type**: implementation | **Depends on**: T-013, T-012

Create `src/gui/scan_panel.py`:

- `ScanPanel(QWidget)`:
  - "Select Window" button → calls `pick_window()` → stores `hwnd`, updates status label to "Window: [title]"
  - "Start Scan" button (disabled until window selected) → starts `ScanWorker`
  - "Cancel" button (hidden until scan starts, replaces Start) → calls `worker.cancel()`
  - `QTextEdit` (read-only, auto-scroll) for log output
  - Emits `scan_complete(list[Hero])` when worker finishes

- `ScanWorker(QThread)`:
  - Runs `run_scan(hwnd, db, on_log, on_hero, check_cancelled)` in background thread
  - Emits `log_message(str)`, `hero_captured(Hero)`, `finished(int)`, `error(str)`

---

### T-017 · Implement MainWindow
**Type**: implementation | **Depends on**: T-015, T-016

Create `src/gui/main_window.py`:

- `MainWindow(QMainWindow)`:
  - `QStackedWidget`: page 0 = `ScanPanel`, page 1 = `HeroBrowser`
  - On `ScanPanel.scan_complete(heroes)`: switch to page 1, call `HeroBrowser.load_heroes(heroes)`
  - Window title: "ProfTracker"
  - Minimum size: 900×600

---

### T-018 · Implement entry point
**Type**: implementation | **Depends on**: T-017, T-005

Create `src/main.py`:

```python
import sys
from PyQt6.QtWidgets import QApplication
from storage.database import Database
from gui.main_window import MainWindow

def main():
    db = Database("proficiency_tracker.db")
    db.connect()
    db.init_schema()
    app = QApplication(sys.argv)
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

### T-019 · Create requirements.txt and project config
**Type**: setup | **Depends on**: none

Create `requirements.txt`:
```
PyQt6>=6.6
Pillow>=10.0
pytesseract>=0.3.10
pywin32>=306
pyautogui>=0.9.54
pytest>=8.0
pytest-qt>=4.4
```

Create `.gitignore`:
```
__pycache__/
*.pyc
.venv/
proficiency_tracker.db
docx_images/
.temp/
*.docx
*.txt
!requirements.txt
```

Create `tests/__init__.py` and `tests/unit/__init__.py` and `tests/integration/__init__.py` (empty).
Create `tests/fixtures/` directory with placeholder `README.md` noting fixture images go here.

---

## Task Order Summary

| Phase | Task  | Description                          | Type            | Status |
|-------|-------|--------------------------------------|-----------------|--------|
| 0     | T-019 | requirements.txt + project config    | setup           | [X]    |
| 0     | T-000 | .temp debug image saving (temporary) | implementation  | [X]    |
| 1     | T-001 | Hero validation tests                | test            | [X]    |
| 1     | T-002 | Storage tests                        | test            | [X]    |
| 1     | T-003 | Hero model implementation            | implementation  | [X]    |
| 1     | T-004 | CaptureRun model implementation      | implementation  | [X]    |
| 1     | T-005 | Database + repository implementation | implementation  | [X]    |
| 2     | T-006 | OCR parser tests                     | test            | [X]    |
| 2     | T-007 | Capture pipeline integration test    | test            | [X]    |
| 2     | T-008 | Clipboard capture implementation     | implementation  | [X]    |
| 2     | T-009 | OCR module implementation            | implementation  | [X]    |
| 2     | T-010 | Window module implementation         | implementation  | [X]    |
| 2     | T-011 | Navigator implementation             | implementation  | [X]    |
| 2     | T-012 | Full capture pipeline                | implementation  | [X]    |
| 3     | T-013 | Window picker overlay                | implementation  | [X]    |
| 4     | T-014 | HeroDetailPanel                      | implementation  | [X]    |
| 4     | T-015 | HeroBrowser                          | implementation  | [X]    |
| 4     | T-016 | ScanPanel + ScanWorker               | implementation  | [X]    |
| 4     | T-017 | MainWindow                           | implementation  | [X]    |
| 4     | T-018 | Entry point (main.py)                | implementation  | [X]    |
