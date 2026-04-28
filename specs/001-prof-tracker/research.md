# Research: ProfTracker — Marvel Rivals Hero Proficiency Tracker

**Date**: 2026-04-18
**Feature**: `specs/001-prof-tracker`

---

## 1. Screen Capture via Windows Clipboard

**Decision**: Use `win32clipboard` + `PIL.ImageGrab.grabclipboard()` to read the image, then `win32clipboard.EmptyClipboard()` to delete it.

**Rationale**: The user explicitly specified clipboard-based capture. The flow is:
1. Focus the target window handle via `win32gui.SetForegroundWindow(hwnd)`
2. Send `Alt+PrintScreen` via `pyautogui.hotkey('alt', 'printscreen')` to push the active window to the clipboard
3. Read with `PIL.ImageGrab.grabclipboard()` → returns a `PIL.Image` object
4. Process the image
5. Clear clipboard immediately: open → empty → close via `win32clipboard`

**Alternatives considered**:
- `mss` library (direct screenshot): rejected — user specified clipboard as the capture method
- `win32ui.CreateDCFromHandle` + `PrintWindow` API: lower-level, no clipboard needed, but doesn't honour the user's clipboard requirement
- Cloud Vision / external OCR API: rejected — user explicitly requires no major API calls

---

## 2. Interactive Window Picker

**Decision**: PyQt6 transparent fullscreen overlay. When user clicks anywhere on screen, resolve `QCursor.pos()` → `win32gui.WindowFromPoint(x, y)` → walk up to top-level window → store `hwnd`.

**Rationale**: Native Qt overlay avoids external dependencies. `win32gui.WindowFromPoint` gives the exact HWND under the cursor. Walking the parent chain with `win32gui.GetParent` ensures we store the top-level game window, not a child widget.

**Flow**:
1. App shows a dialog: "Click the Marvel Rivals window to select it"
2. On confirmation, a semi-transparent fullscreen `QWidget` (always-on-top, click-through borders) is shown
3. User clicks the game window
4. Overlay captures the click coordinates, resolves HWND, stores it, and closes
5. App confirms: "Marvel Rivals window selected (HWND: XXXXXX)"

**Alternatives considered**:
- Enumerate all windows and show a dropdown: usable but requires user to identify the correct entry by title
- `pygetwindow` library: thin wrapper, adds a dependency without adding value over direct pywin32

---

## 3. OCR Engine

**Decision**: Tesseract 5.x via `pytesseract` (local installation required on user machine).

**Rationale**: Fully local, no API calls, well-supported on Windows. Tesseract 5 uses LSTM models with better accuracy than 4.x. Image preprocessing (greyscale, threshold, upscale) with `Pillow` improves accuracy on game UI text.

**Preprocessing pipeline** (per captured region):
1. Crop to the relevant UI region
2. Convert to greyscale
3. Apply threshold (binarize) to increase contrast
4. Upscale 2x for better character recognition
5. Run `pytesseract.image_to_data()` with `--psm 6` (uniform block of text)

**Alternatives considered**:
- `easyocr`: higher accuracy out-of-box but large model download (~200 MB GPU model); overkill for structured game UI
- Windows OCR API (`Windows.Media.Ocr`): available natively but requires WinRT bindings; more complex setup
- Cloud Vision APIs: rejected — no major API calls allowed

---

## 4. UI Automation (In-Game Navigation)

**Decision**: `pyautogui` for simulated mouse clicks and keyboard inputs to navigate the hero proficiency screen in Marvel Rivals.

**Rationale**: `pyautogui` is cross-platform but works reliably on Windows for game UI automation. Combined with `win32gui.SetForegroundWindow`, we can focus the game window before sending inputs.

**Scroll strategy**: The hero proficiency list requires scrolling. Use `pyautogui.scroll()` within the game window's bounds, with configurable delay between actions (default 0.5s) to allow the game UI to render.

**Alternatives considered**:
- `pywin32` `SendMessage`/`PostMessage`: works for some Windows controls, unreliable for game engines
- `keyboard` + `mouse` libraries: lighter than pyautogui but require separate install; pyautogui covers both

---

## 5. GUI Framework

**Decision**: PyQt6

**Rationale**: Native-looking Windows widgets, strong layout system, `QThread` for background scan work without freezing the UI, built-in `QProgressBar` and `QListWidget` for the hero browser.

**Key UI patterns**:
- `QThread` + signals/slots for scan worker (keeps GUI responsive)
- `QSplitter` for sidebar (hero list) + detail panel layout
- `QTextEdit` (append-only, auto-scroll) for real-time scan log

---

## 6. Local Storage

**Decision**: SQLite via Python's built-in `sqlite3` module. Database file: `proficiency_tracker.db` in the application directory.

**Rationale**: No server, no setup, zero dependencies. `sqlite3` is in the standard library. Sufficient for ~50 heroes × N scan runs of structured records.

**Alternatives considered**:
- JSON flat file: no query capability, fragile for concurrent writes
- PostgreSQL/MySQL: requires server; vastly over-engineered for a single-user local app

---

## 7. Dependencies Summary

| Package        | Version  | Purpose                                      | Install                        |
|----------------|----------|----------------------------------------------|--------------------------------|
| PyQt6          | ≥6.6     | Desktop GUI                                  | `pip install PyQt6`            |
| Pillow         | ≥10.0    | Image capture, crop, preprocessing           | `pip install Pillow`           |
| pytesseract    | ≥0.3.10  | Python bindings for Tesseract OCR            | `pip install pytesseract`      |
| pywin32        | ≥306     | Window handle resolution, clipboard control  | `pip install pywin32`          |
| pyautogui      | ≥0.9.54  | In-game mouse/keyboard automation            | `pip install pyautogui`        |
| pytest         | ≥8.0     | Test runner                                  | `pip install pytest`           |
| pytest-qt      | ≥4.4     | PyQt6 GUI testing                            | `pip install pytest-qt`        |

**System requirement**: Tesseract 5.x installed separately (https://github.com/UB-Mannheim/tesseract/wiki)

---

## 8. No External API Calls

All processing is local:
- OCR: Tesseract running on-device
- Image capture: Windows clipboard API
- Storage: local SQLite file
- No network calls at runtime

This satisfies the explicit constraint: "no major API calls."
