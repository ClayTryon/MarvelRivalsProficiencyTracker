import threading
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit,
)
from PyQt6.QtCore import pyqtSignal

from capture import navigator
from capture.pipeline import run_scan
from capture.window_picker import pick_window
from models.hero import Hero
from storage.database import Database
from storage.repository import HeroRepository


class ScanPanel(QWidget):
    scan_complete  = pyqtSignal(list)
    hwnd_selected  = pyqtSignal(int)

    _log_sig          = pyqtSignal(str)
    _hero_sig         = pyqtSignal(object)
    _scan_finished_sig = pyqtSignal(int)
    _scan_failed_sig  = pyqtSignal(str)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db = db
        self._hwnd: int | None = None
        self._heroes: list[Hero] = []
        self._scan_cancelled = False
        self._pre_scan_xp: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("PROFICIENCY SCANNER")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 20px; letter-spacing: 4px; color: #f4d641;"
        )
        layout.addWidget(title)

        self._status_label = QLabel("No window selected.")
        self._status_label.setStyleSheet("color: #484860; font-size: 12px;")
        layout.addWidget(self._status_label)

        checklist = QLabel(
            "Before scanning:  Marvel Rivals must be open on the "
            "Heroes grid, scrolled to the top  ·  "
            "Display Mode: Windowed  ·  Resolution: 1920 × 1080"
        )
        checklist.setWordWrap(True)
        checklist.setStyleSheet(
            "color: #b0903a; background: #1a1400; border: 1px solid #3a2e00;"
            " border-radius: 4px; padding: 6px 10px; font-size: 11px;"
        )
        layout.addWidget(checklist)

        btn_row = QHBoxLayout()
        self._select_btn = QPushButton("Select Window")
        self._auto_scan_btn = QPushButton("Auto Scan")
        self._auto_scan_btn.setEnabled(False)
        self._auto_scan_btn.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self._cancel_btn = QPushButton("Cancel Scan")
        self._cancel_btn.setStyleSheet("color: #f88; padding: 6px 14px;")
        self._cancel_btn.setVisible(False)
        btn_row.addWidget(self._select_btn)
        btn_row.addWidget(self._auto_scan_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Session log will appear here...")
        layout.addWidget(self._log)

        self._select_btn.clicked.connect(self._select_window)
        self._auto_scan_btn.clicked.connect(self._start_auto_scan)
        self._cancel_btn.clicked.connect(self._cancel_auto_scan)

        self._log_sig.connect(self._append_log)
        self._hero_sig.connect(self._on_auto_hero)
        self._scan_finished_sig.connect(self._on_scan_finished)
        self._scan_failed_sig.connect(self._on_scan_failed)

    # ------------------------------------------------------------------
    # Window selection
    # ------------------------------------------------------------------

    def _select_window(self):
        result = pick_window(parent=self)
        if result:
            hwnd, title = result
            self._hwnd = hwnd
            self._status_label.setText(f"Window: {title}")
            self._auto_scan_btn.setEnabled(True)
            self.hwnd_selected.emit(hwnd)

    # ------------------------------------------------------------------
    # Pre/post scan XP delta
    # ------------------------------------------------------------------

    def _snapshot_pre_scan(self):
        from data.xp_table import total_xp_earned
        self._pre_scan_xp = {
            h.name: total_xp_earned(h.level, h.xp)
            for h in HeroRepository(self._db).get_all()
        }

    def _show_scan_delta(self, heroes: list):
        if not heroes:
            return
        from data.xp_table import total_xp_earned
        lines = []
        for h in sorted(heroes, key=lambda x: x.name):
            after_xp  = total_xp_earned(h.level, h.xp)
            before_xp = self._pre_scan_xp.get(h.name)
            if before_xp is None:
                lines.append(f"  {h.name}: new  LV{h.level}")
            else:
                delta = after_xp - before_xp
                if delta > 0:
                    lines.append(f"  {h.name}: +{delta:,} XP")
        if lines:
            self._append_log("─── Changes since last scan ───\n" + "\n".join(lines))
        self._pre_scan_xp = {}

    # ------------------------------------------------------------------
    # Auto scan
    # ------------------------------------------------------------------

    def _start_auto_scan(self):
        from data.heroes import is_synced
        if not is_synced():
            self._append_log(
                "ERROR: Hero roster not found.\n"
                "Please go to the Sync tab and run Wiki Sync before scanning."
            )
            return

        self._snapshot_pre_scan()
        self._heroes = []
        self._scan_cancelled = False

        self._select_btn.setEnabled(False)
        self._auto_scan_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        self._append_log(
            "Auto scan starting.\n"
            "Move your mouse once, then press any key to register input devices.\n"
            "You will have 4 seconds to switch to the game after device detection."
        )

        threading.Thread(target=self._auto_scan_thread, daemon=True).start()

    def _cancel_auto_scan(self):
        self._scan_cancelled = True
        self._append_log("Cancelling scan...")

    def _auto_scan_thread(self):
        db = Database(self._db.db_path)
        db.connect()
        try:
            navigator.enable()
            self._log_sig.emit("Devices registered. Switching to game in 4 seconds...")
            time.sleep(4)

            count = run_scan(
                self._hwnd,
                db,
                on_log=self._log_sig.emit,
                on_hero=self._hero_sig.emit,
                check_cancelled=lambda: self._scan_cancelled,
            )
            self._scan_finished_sig.emit(count)
        except Exception as e:
            self._scan_failed_sig.emit(str(e))
        finally:
            navigator.disable()
            db.close()

    def _on_auto_hero(self, hero: Hero):
        self._heroes.append(hero)

    def _on_scan_finished(self, count: int):
        self._append_log(f"Auto scan complete — {count} heroes captured.")
        self._show_scan_delta(self._heroes)
        self._reset_auto_scan_ui()
        self.scan_complete.emit(self._heroes)

    def _on_scan_failed(self, error: str):
        self._append_log(f"Auto scan failed: {error}")
        self._reset_auto_scan_ui()

    def _reset_auto_scan_ui(self):
        self._cancel_btn.setVisible(False)
        self._select_btn.setEnabled(True)
        self._auto_scan_btn.setEnabled(True)

    # ------------------------------------------------------------------

    def _append_log(self, text: str):
        self._log.append(text)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )
