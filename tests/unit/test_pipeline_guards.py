import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from unittest.mock import patch, MagicMock
from exceptions import CaptureError


def _make_db():
    from storage.database import Database
    db = Database(":memory:")
    db.connect()
    db.init_schema()
    return db


def test_run_scan_raises_capture_error_when_not_synced():
    """run_scan must raise CaptureError immediately if is_synced() returns False."""
    from capture.pipeline import run_scan

    db = _make_db()
    with patch("capture.pipeline.is_synced", return_value=False):
        with pytest.raises(CaptureError, match="roster"):
            run_scan(
                hwnd=1,
                db=db,
                on_log=lambda _: None,
                on_hero=lambda *_: None,
                check_cancelled=lambda: False,
            )
