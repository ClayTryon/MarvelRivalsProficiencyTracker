# Quickstart: ProfTracker

## Prerequisites

1. **Python 3.11+** — https://www.python.org/downloads/
2. **Tesseract 5.x** — https://github.com/UB-Mannheim/tesseract/wiki
   - During install, note the path (default: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
3. **Marvel Rivals** installed and able to run on the same machine

## Setup

```bash
# Clone / navigate to project
cd ProficiencyTracker

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configure Tesseract Path

If Tesseract is not on your system PATH, set it before running:

```python
# src/capture/ocr.py reads this from an env var or falls back to the default path
# Option 1: set env var
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Option 2: it defaults to the path above automatically on Windows
```

## Run the Application

```bash
python src/main.py
```

## First-Time Use

1. Launch **Marvel Rivals** and leave it running (can be on any screen)
2. Launch **ProfTracker**
3. Click **"Select Window"** — a transparent overlay appears
4. Click anywhere on the **Marvel Rivals window**
5. ProfTracker confirms the window is selected
6. Navigate to the hero proficiency screen in Marvel Rivals
7. Click **"Start Scan"** in ProfTracker
8. Watch the real-time log as heroes are captured
9. Browse results in the hero list after the scan completes

## Run Tests

```bash
pytest tests/ -v
```

## Project Structure

```
src/
├── main.py                    # Entry point
├── models/
│   ├── hero.py                # Hero dataclass + validation
│   └── capture_run.py         # CaptureRun dataclass + status enum
├── capture/
│   ├── window_picker.py       # Fullscreen Qt overlay for window selection
│   ├── window.py              # Win32 window focus and validation
│   ├── clipboard_capture.py   # Clipboard screenshot + clear
│   ├── navigator.py           # pyautogui in-game navigation
│   └── ocr.py                 # Tesseract OCR + Hero record parsing
├── storage/
│   ├── database.py            # SQLite connection + schema init
│   └── repository.py          # Hero + CaptureRun CRUD
└── gui/
    ├── main_window.py         # QMainWindow layout
    ├── scan_panel.py          # Start/Cancel button + log
    ├── hero_browser.py        # Sidebar list + detail panel
    └── hero_detail.py         # Hero name, role, level, XP, progress bar

tests/
├── unit/
│   ├── test_hero_validation.py
│   ├── test_ocr_parser.py
│   └── test_storage.py
└── integration/
    └── test_capture_pipeline.py
```
