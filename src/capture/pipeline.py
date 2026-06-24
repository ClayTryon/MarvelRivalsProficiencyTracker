"""
Scan pipeline — navigates the Marvel Rivals heroes grid and captures proficiency data.

Two-phase design:
  Phase 1 — navigate every hero card, screenshot the proficiency tab, store images in memory.
  Phase 2 — run OCR on all collected images and persist results to the database.

Separating navigation from OCR means the game window is held for the minimum possible time.
The caller is responsible for calling navigator.enable() / navigator.disable() around run_scan().
"""
import time
import threading
from datetime import datetime, timezone

from capture import clipboard_capture, ocr, navigator
from capture.window import is_window_alive
from capture.debug import save_debug_image, clear_temp
from storage.database import Database
from storage.repository import HeroRepository, CaptureRunRepository, SnapshotRepository
from models.hero import Hero
from models.capture_run import CaptureStatus
from exceptions import CaptureError, ParseError, ValidationError
from data.heroes import HERO_ROSTER, HERO_ROLES, is_synced

_GRID_COLS = 7
_GRID_ROWS = 2

# Hero card centres as fractions of client area width/height
_COL_CENTERS = [0.155, 0.274, 0.387, 0.506, 0.620, 0.733, 0.847]
_ROW_CENTERS = [0.358, 0.707]

# Proficiency tab and sub-tabs
_PROFICIENCY_TAB_X = 0.434
_PROFICIENCY_TAB_Y = 0.041
_MISSIONS_TAB_X = 0.435
_MISSIONS_TAB_Y = 0.085


def _start_backspace_listener() -> tuple[threading.Event, threading.Event]:
    """Start a background thread that sets cancel_event when backspace is pressed.

    Uses a second Interception context so the keypress is visible even while the
    driver is actively capturing keyboard input for the scan. All strokes are
    passed through so the game still receives them.

    Returns (cancel_event, stop_event). Caller must set stop_event when done.
    """
    cancel_event = threading.Event()
    stop_event = threading.Event()

    _BACKSPACE_SCAN_CODE = 14  # PS/2 scan code for backspace

    def _poll():
        try:
            from interception.inputs import Interception, FilterKeyFlag, KeyStroke
            ctx = Interception()
            ctx.set_filter(ctx.is_keyboard, FilterKeyFlag.FILTER_KEY_DOWN)
            try:
                while not stop_event.is_set():
                    device = ctx.await_input(timeout_milliseconds=50)
                    if device is None:
                        continue
                    stroke = ctx.devices[device].receive()
                    if stroke is None:
                        continue
                    if isinstance(stroke, KeyStroke) and stroke.code == _BACKSPACE_SCAN_CODE:
                        cancel_event.set()
                    ctx.send(device, stroke)
            finally:
                ctx.destroy()
        except Exception:
            pass

    threading.Thread(target=_poll, daemon=True).start()
    return cancel_event, stop_event



def _build_and_save_hero(hero_name: str, capture_run_id: int, level: int,
                         xp: int, xp_req: int, is_max: bool,
                         repo: HeroRepository, snapshot_repo: SnapshotRepository) -> Hero:
    hero = Hero(
        name=hero_name,
        role=HERO_ROLES.get(hero_name, "Unknown"),
        level=level,
        xp=xp,
        xp_required=xp_req,
        is_max_level=is_max,
        capture_run_id=capture_run_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    hero.validate()
    repo.upsert(hero)
    snapshot_repo.insert(hero)
    return hero


def capture_one_hero_from_image(image, db: Database, capture_run_id: int, hero_name: str) -> Hero:
    """OCR a pre-captured PIL Image (e.g. from clipboard) for a single hero."""
    save_debug_image(image, "proficiency_raw_clipboard")
    _name, level, xp, xp_req, is_max = ocr.parse_proficiency_bar(image)
    return _build_and_save_hero(hero_name, capture_run_id, level, xp, xp_req, is_max,
                                HeroRepository(db), SnapshotRepository(db))


def run_scan(hwnd: int, db: Database, on_log, on_hero, check_cancelled) -> int:
    """Automatically scan every hero in HERO_ROSTER and persist proficiency data.

    Expects navigator devices to already be registered by the caller.

    on_log(str)   — called with status messages for the UI log
    on_hero(Hero) — called for each successfully parsed hero (Phase 2)
    check_cancelled() → bool — return True to abort mid-scan

    Returns the number of heroes successfully captured.
    """
    if not is_synced():
        raise CaptureError(
            "Hero roster not found. Please run Wiki Sync before scanning."
        )
    if not is_window_alive(hwnd):
        raise CaptureError("Target window is no longer alive")

    clear_temp()
    scan_roster = list(HERO_ROSTER)
    run_repo = CaptureRunRepository(db)
    hero_repo = HeroRepository(db)
    snapshot_repo = SnapshotRepository(db)
    capture_run = run_repo.create()
    hero_count = 0

    backspace_event, stop_listener = _start_backspace_listener()

    def _cancelled():
        return check_cancelled() or backspace_event.is_set()

    try:
        clipboard_capture.focus_window(hwnd)
        on_log("Starting scan from heroes grid...")

        # --- Phase 1: navigate and capture all screenshots ---
        captures: list[tuple[str, object]] = []
        page_size = _GRID_COLS * _GRID_ROWS
        roster_offset = 0

        while roster_offset < len(scan_roster):
            page = roster_offset // page_size + 1
            on_log(f"Capturing page {page}...")

            for idx in range(page_size):
                roster_idx = roster_offset + idx
                if roster_idx >= len(scan_roster):
                    break

                if _cancelled():
                    on_log("Scan cancelled.")
                    run_repo.update_status(capture_run.id, CaptureStatus.CANCELLED)
                    return hero_count

                hero_name = scan_roster[roster_idx]
                col, row = idx % _GRID_COLS, idx // _GRID_COLS
                cx, cy = _COL_CENTERS[col], _ROW_CENTERS[row]

                navigator.click_at(hwnd, cx, cy, delay=0.1)
                navigator.press_space()
                time.sleep(0.8)
                navigator.click_at(hwnd, _PROFICIENCY_TAB_X, _PROFICIENCY_TAB_Y, delay=0.15)
                navigator.click_at(hwnd, _MISSIONS_TAB_X, _MISSIONS_TAB_Y, delay=0.15)

                prof_image = None
                for attempt in range(3):
                    if attempt > 0:
                        time.sleep(0.5 * attempt)  # 0.5s, then 1.0s
                        navigator.click_at(hwnd, _PROFICIENCY_TAB_X, _PROFICIENCY_TAB_Y, delay=0.15)
                        navigator.click_at(hwnd, _MISSIONS_TAB_X, _MISSIONS_TAB_Y, delay=0.15)
                    clipboard_capture.focus_window(hwnd)
                    candidate = navigator.capture_active_window(hwnd)
                    try:
                        ocr.parse_proficiency_bar(candidate, save_debug=False)
                        prof_image = candidate
                        break
                    except ParseError:
                        prof_image = candidate
                        if attempt < 2:
                            on_log(f"  retrying {hero_name}...")

                save_debug_image(prof_image, f"prof_{hero_name.replace(' ', '_')}")
                captures.append((hero_name, prof_image))
                on_log(f"  captured {hero_name}")

                navigator.press_escape()
                time.sleep(0.2)

            roster_offset += page_size
            if roster_offset < len(scan_roster):
                navigator.scroll_down(amount=3)
                time.sleep(1)

        on_log(f"All {len(captures)} screenshots captured. Processing...")

        # --- Phase 2: OCR and persist ---
        for hero_name, prof_image in captures:
            if _cancelled():
                on_log("Scan cancelled.")
                run_repo.update_status(capture_run.id, CaptureStatus.CANCELLED)
                return hero_count

            try:
                _, level, xp, xp_req, is_max = ocr.parse_proficiency_bar(prof_image)
                hero = _build_and_save_hero(hero_name, capture_run.id, level, xp, xp_req,
                                            is_max, hero_repo, snapshot_repo)
                hero_count += 1
                on_hero(hero)
                on_log(f"✓ {hero_name} LV{level}")
            except (ParseError, ValidationError) as e:
                on_log(f"✗ {hero_name}: {e}")

        run_repo.update_status(capture_run.id, CaptureStatus.COMPLETED, hero_count=hero_count)
        on_log(f"Scan complete. {hero_count} heroes captured.")
        return hero_count

    except CaptureError:
        run_repo.update_status(capture_run.id, CaptureStatus.FAILED)
        raise
    except Exception as e:
        run_repo.update_status(capture_run.id, CaptureStatus.FAILED, error_message=str(e))
        raise
    finally:
        stop_listener.set()
