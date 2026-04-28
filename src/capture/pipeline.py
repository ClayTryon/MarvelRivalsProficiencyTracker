import time
import random
from datetime import datetime, timezone

from capture import clipboard_capture, ocr, navigator
from capture.window import is_window_alive
from capture.debug import save_debug_image, clear_temp
from storage.database import Database
from storage.repository import HeroRepository, CaptureRunRepository
from models.hero import Hero
from models.capture_run import CaptureStatus
from exceptions import CaptureError, ParseError, ValidationError
from data.heroes import HERO_ROSTER, HERO_ROLES

# Relative positions of the HEROES nav button (measured from 1936×1119 window)
_HEROES_BTN_X = 0.346
_HEROES_BTN_Y = 0.054

# Grid layout: 7 columns × 2 rows
_GRID_COLS = 7
_GRID_ROWS = 2

# Hero card center positions as fractions of window (measured from 1936×1119 window)
# Columns at px: 300, 530, 750, 980, 1200, 1420, 1640
# Rows at px: 420, 800
_COL_CENTERS = [0.155, 0.274, 0.387, 0.506, 0.620, 0.733, 0.847]
_ROW_CENTERS = [0.375, 0.715]

# Proficiency tab relative position (measured from 1936×1119 window, px: 840x75)
_PROFICIENCY_TAB_X = 0.434
_PROFICIENCY_TAB_Y = 0.067


def _card_center_pct(col: int, row: int) -> tuple[float, float]:
    return _COL_CENTERS[col], _ROW_CENTERS[row]


def _build_and_save_hero(hero_name: str, capture_run_id: int, level: int,
                         xp: int, xp_req: int, is_max: bool, repo: HeroRepository) -> Hero:
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
    return hero


def capture_one_hero(hwnd: int, db: Database, capture_run_id: int, hero_name: str) -> Hero:
    if not is_window_alive(hwnd):
        raise CaptureError("Target window is no longer alive")

    image = clipboard_capture.capture_window(hwnd)
    save_debug_image(image, "proficiency_raw")
    save_debug_image(ocr.preprocess(image.crop(ocr.XP_REGION)), "proficiency_xp_crop")
    # _easyocr_level() inside parse_proficiency_bar saves its own "level_ocr_input" debug image

    _name, level, xp, xp_req, is_max = ocr.parse_proficiency_bar(image)
    return _build_and_save_hero(hero_name, capture_run_id, level, xp, xp_req, is_max,
                                HeroRepository(db))


def run_scan(hwnd: int, db: Database, on_log, on_hero, check_cancelled) -> int:
    if not is_window_alive(hwnd):
        raise CaptureError("Target window is no longer alive")

    clear_temp()
    run_repo = CaptureRunRepository(db)
    hero_repo = HeroRepository(db)
    capture_run = run_repo.create()
    hero_count = 0

    try:
        navigator.enable()
        clipboard_capture.focus_window(hwnd)
        on_log("Starting scan from heroes grid...")

        # --- Phase 1: navigate and capture all screenshots ---
        captures: list[tuple[str, object]] = []
        page_size = _GRID_COLS * _GRID_ROWS
        roster_offset = 0

        while roster_offset < len(HERO_ROSTER):
            page = roster_offset // page_size + 1
            on_log(f"Capturing page {page}...")

            for idx in range(page_size):
                roster_idx = roster_offset + idx
                if roster_idx >= len(HERO_ROSTER):
                    break

                if check_cancelled():
                    on_log("Scan cancelled.")
                    run_repo.update_status(capture_run.id, CaptureStatus.CANCELLED)
                    return hero_count

                hero_name = HERO_ROSTER[roster_idx]
                col, row = idx % _GRID_COLS, idx // _GRID_COLS
                cx, cy = _card_center_pct(col, row)

                clipboard_capture.focus_window(hwnd)
                navigator.click_at(hwnd, cx, cy, delay=0.35 + random.uniform(0, 0.08))

                clipboard_capture.focus_window(hwnd)
                navigator.press_space(hwnd)
                time.sleep(0.35 + random.uniform(0, 0.08))

                clipboard_capture.focus_window(hwnd)
                navigator.click_at(hwnd, _PROFICIENCY_TAB_X, _PROFICIENCY_TAB_Y, delay=0.35 + random.uniform(0, 0.08))

                prof_image = clipboard_capture.capture_window(hwnd)
                save_debug_image(prof_image, f"prof_{hero_name.replace(' ', '_')}")
                captures.append((hero_name, prof_image))
                on_log(f"  captured {hero_name}")

                clipboard_capture.focus_window(hwnd)
                navigator.press_escape(hwnd)
                time.sleep(0.35 + random.uniform(0, 0.08))

            roster_offset += page_size
            if roster_offset < len(HERO_ROSTER):
                navigator.scroll_down(hwnd, amount=3)
                time.sleep(0.6 + random.uniform(0, 0.1))

        on_log(f"All {len(captures)} screenshots captured. Processing...")

        # --- Phase 2: OCR and persist ---
        for hero_name, prof_image in captures:
            if check_cancelled():
                on_log("Scan cancelled.")
                run_repo.update_status(capture_run.id, CaptureStatus.CANCELLED)
                return hero_count

            try:
                _, level, xp, xp_req, is_max = ocr.parse_proficiency_bar(prof_image)
                hero = _build_and_save_hero(hero_name, capture_run.id, level, xp, xp_req,
                                            is_max, hero_repo)
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
        navigator.disable()
