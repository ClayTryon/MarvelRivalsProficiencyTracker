import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from storage.database import Database
from storage.repository import HeroRepository, CaptureRunRepository


def make_blank_image(w=1920, h=1080):
    return Image.new("RGB", (w, h), (20, 20, 20))


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.connect()
    database.init_schema()
    return database


@pytest.fixture
def hero_repo(db):
    return HeroRepository(db)


# Patch targets use capture.pipeline.* because pipeline imports functions directly
_BASE = "capture.pipeline"

_SMALL_ROSTER = ["CAPTAIN AMERICA", "IRON MAN"]


def _base_patches(blank):
    return [
        patch(f"{_BASE}.is_window_alive", return_value=True),
        patch(f"{_BASE}.HERO_ROSTER", _SMALL_ROSTER),
        patch(f"{_BASE}.clear_temp"),
        patch("capture.clipboard_capture.focus_window"),
        patch("capture.clipboard_capture.capture_window", return_value=blank),
        patch(f"{_BASE}.navigator.click_at"),
        patch(f"{_BASE}.navigator.press_space"),
        patch(f"{_BASE}.navigator.press_escape"),
        patch(f"{_BASE}.navigator.scroll_down"),
        patch(f"{_BASE}.save_debug_image"),
        patch(f"{_BASE}.time.sleep"),
    ]


def test_run_scan_returns_heroes_and_stores_them(db, hero_repo):
    from capture.pipeline import run_scan

    blank = make_blank_image()
    prof_side_effects = [
        ("", 11, 44, 400, False),
        ("", 20, 100, 500, False),
    ]

    log_messages = []
    captured_heroes = []

    patches = _base_patches(blank)
    patches += [
        patch(f"{_BASE}.ocr.parse_proficiency_bar", side_effect=prof_side_effects),
    ]

    with _apply(*patches):
        count = run_scan(
            hwnd=12345, db=db,
            on_log=log_messages.append,
            on_hero=captured_heroes.append,
            check_cancelled=lambda: False,
        )

    assert count == 2
    assert len(captured_heroes) == 2
    stored = hero_repo.get_all()
    assert len(stored) == 2
    names = {h.name for h in stored}
    assert "CAPTAIN AMERICA" in names
    assert "IRON MAN" in names


def test_run_scan_raises_on_dead_hwnd(db):
    from capture.pipeline import run_scan
    from exceptions import CaptureError

    with patch(f"{_BASE}.is_window_alive", return_value=False):
        with pytest.raises(CaptureError, match="window"):
            run_scan(hwnd=0, db=db, on_log=lambda m: None,
                     on_hero=lambda h: None, check_cancelled=lambda: False)


def test_run_scan_skips_hero_on_parse_error(db, hero_repo):
    from capture.pipeline import run_scan
    from exceptions import ParseError

    blank = make_blank_image()
    log_messages = []

    patches = _base_patches(blank)
    patches += [
        patch(f"{_BASE}.ocr.parse_proficiency_bar", side_effect=[
            ParseError("bad read"),
            ("", 20, 100, 500, False),
        ]),
    ]

    with _apply(*patches):
        count = run_scan(
            hwnd=12345, db=db,
            on_log=log_messages.append,
            on_hero=lambda h: None,
            check_cancelled=lambda: False,
        )

    assert count == 1
    assert any("CAPTAIN AMERICA" in m for m in log_messages)


def test_run_scan_respects_cancel(db):
    from capture.pipeline import run_scan

    blank = make_blank_image()
    captured = []

    patches = _base_patches(blank)
    patches += [
        patch(f"{_BASE}.ocr.parse_proficiency_bar", return_value=("", 11, 44, 400, False)),
    ]

    with _apply(*patches):
        count = run_scan(
            hwnd=12345, db=db,
            on_log=lambda m: None,
            on_hero=captured.append,
            check_cancelled=lambda: True,
        )

    assert count == 0


class _apply:
    """Context manager that stacks multiple patch objects."""
    def __init__(self, *patches):
        self._patches = patches
        self._mocks = []

    def __enter__(self):
        try:
            for p in self._patches:
                self._mocks.append(p.__enter__())
        except Exception:
            for p in reversed(self._patches[:len(self._mocks)]):
                p.__exit__(None, None, None)
            raise
        return self._mocks

    def __exit__(self, *args):
        for p in reversed(self._patches):
            p.__exit__(*args)
