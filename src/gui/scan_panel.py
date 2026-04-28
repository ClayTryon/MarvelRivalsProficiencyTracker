import threading
import time
import win32api
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from data.heroes import HERO_ROSTER
from models.hero import Hero
from storage.database import Database


class ScanPanel(QWidget):
    scan_complete = pyqtSignal(list)
    back_requested = pyqtSignal()

    # Cross-thread signals for auto scan
    _log_sig = pyqtSignal(str)
    _hero_sig = pyqtSignal(object)
    _scan_finished_sig = pyqtSignal(int)
    _scan_failed_sig = pyqtSignal(str)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db = db
        self._hwnd: int | None = None
        self._heroes: list[Hero] = []
        self._capture_run_id: int | None = None
        self._session_active = False
        self._key2_was_down = False
        self._scan_cancelled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("ProfTracker — Marvel Rivals")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        self._back_btn = QPushButton("← Back to Results")
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        header_row.addWidget(self._back_btn)
        layout.addLayout(header_row)

        self._status_label = QLabel("No window selected.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        # Setup row
        setup_row = QHBoxLayout()
        self._select_btn = QPushButton("Select Window")
        self._start_btn = QPushButton("Start Session")
        self._start_btn.setEnabled(False)
        self._auto_scan_btn = QPushButton("Auto Scan")
        self._auto_scan_btn.setEnabled(False)
        self._auto_scan_btn.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self._cancel_btn = QPushButton("Cancel Scan")
        self._cancel_btn.setStyleSheet("color: #f88; padding: 6px 14px;")
        self._cancel_btn.setVisible(False)
        setup_row.addWidget(self._select_btn)
        setup_row.addWidget(self._start_btn)
        setup_row.addWidget(self._auto_scan_btn)
        setup_row.addWidget(self._cancel_btn)
        setup_row.addStretch()
        layout.addLayout(setup_row)

        # Session row — hidden until manual session starts
        session_row = QHBoxLayout()
        self._hero_combo = QComboBox()
        self._hero_combo.addItems(sorted(HERO_ROSTER))
        self._hero_combo.setMinimumWidth(180)
        self._capture_btn = QPushButton("2 · Capture Proficiency")
        self._capture_btn.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self._rescan_btn = QPushButton("↺ Rescan")
        self._rescan_btn.setStyleSheet("color: #aaa; padding: 6px 10px;")
        self._rescan_btn.setEnabled(False)
        self._finish_btn = QPushButton("Finish")

        for w in (self._hero_combo, self._capture_btn, self._rescan_btn, self._finish_btn):
            w.setVisible(False)
        session_row.addWidget(self._hero_combo)
        session_row.addWidget(self._capture_btn)
        session_row.addWidget(self._rescan_btn)
        session_row.addWidget(self._finish_btn)
        session_row.addStretch()
        layout.addLayout(session_row)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Session log will appear here...")
        layout.addWidget(self._log)

        self._select_btn.clicked.connect(self._select_window)
        self._start_btn.clicked.connect(self._start_session)
        self._auto_scan_btn.clicked.connect(self._start_auto_scan)
        self._cancel_btn.clicked.connect(self._cancel_auto_scan)
        self._capture_btn.clicked.connect(self._capture_proficiency)
        self._rescan_btn.clicked.connect(self._capture_proficiency)
        self._finish_btn.clicked.connect(self._finish_session)

        self._log_sig.connect(self._append_log)
        self._hero_sig.connect(self._on_auto_hero)
        self._scan_finished_sig.connect(self._on_scan_finished)
        self._scan_failed_sig.connect(self._on_scan_failed)

        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.setInterval(100)
        self._hotkey_timer.timeout.connect(self._poll_hotkeys)

    # ------------------------------------------------------------------
    # Hotkey polling
    # ------------------------------------------------------------------

    def _poll_hotkeys(self):
        try:
            key2_down = bool(win32api.GetAsyncKeyState(0x32) & 0x8000)  # '2'
            if key2_down and not self._key2_was_down:
                self._capture_proficiency()
            self._key2_was_down = key2_down
        except Exception as e:
            self._append_log(f"✗ Hotkey error: {e}")

    # ------------------------------------------------------------------
    # Window selection
    # ------------------------------------------------------------------

    def _select_window(self):
        from capture.window_picker import pick_window
        result = pick_window(parent=self)
        if result:
            hwnd, title = result
            self._hwnd = hwnd
            self._status_label.setText(f"Window: {title}")
            self._start_btn.setEnabled(True)
            self._auto_scan_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Manual session lifecycle
    # ------------------------------------------------------------------

    def _start_session(self):
        from storage.repository import CaptureRunRepository
        from capture.debug import clear_temp
        self._heroes = []
        clear_temp()

        db = Database(self._db.db_path)
        db.connect()
        run = CaptureRunRepository(db).create()
        self._capture_run_id = run.id
        db.close()

        win = self.window()
        win.setWindowFlags(win.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        win.resize(560, 260)
        win.show()

        self._select_btn.setEnabled(False)
        self._start_btn.setVisible(False)
        self._auto_scan_btn.setVisible(False)
        for w in (self._hero_combo, self._capture_btn, self._rescan_btn, self._finish_btn):
            w.setVisible(True)

        self._session_active = True
        self._key2_was_down = False
        self._hotkey_timer.start()
        self._append_log(
            "Session started.\n"
            "Select a hero from the dropdown, navigate to their Proficiency tab, then press 2."
        )

    def _finish_session(self):
        from storage.repository import CaptureRunRepository
        from models.capture_run import CaptureStatus

        self._session_active = False
        self._hotkey_timer.stop()

        db = Database(self._db.db_path)
        db.connect()
        CaptureRunRepository(db).update_status(
            self._capture_run_id, CaptureStatus.COMPLETED, hero_count=len(self._heroes)
        )
        db.close()

        win = self.window()
        win.setWindowFlags(win.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        win.resize(900, 600)
        win.show()

        self._select_btn.setEnabled(True)
        self._start_btn.setVisible(True)
        self._auto_scan_btn.setVisible(True)
        for w in (self._hero_combo, self._capture_btn, self._rescan_btn, self._finish_btn):
            w.setVisible(False)

        self._append_log(f"Session complete — {len(self._heroes)} heroes captured.")
        self.scan_complete.emit(self._heroes)

    # ------------------------------------------------------------------
    # Manual capture
    # ------------------------------------------------------------------

    def _capture_proficiency(self):
        from capture.pipeline import capture_one_hero

        hero_name = self._hero_combo.currentText()
        db = Database(self._db.db_path)
        db.connect()
        try:
            hero = capture_one_hero(self._hwnd, db, self._capture_run_id, hero_name)
            self._heroes.append(hero)
            xp_str = "MAX" if hero.is_max_level else f"{hero.xp}/{hero.xp_required} XP"
            self._append_log(f"✓ {hero.name}  LV{hero.level}  {xp_str}")
            self._rescan_btn.setEnabled(True)
        except Exception as e:
            self._append_log(f"✗ {hero_name}: {e}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Auto scan
    # ------------------------------------------------------------------

    def _start_auto_scan(self):
        self._heroes = []
        self._scan_cancelled = False

        self._select_btn.setEnabled(False)
        self._start_btn.setEnabled(False)
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
        from capture import navigator
        from capture.pipeline import run_scan

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
        self._reset_auto_scan_ui()
        self.scan_complete.emit(self._heroes)

    def _on_scan_failed(self, error: str):
        self._append_log(f"Auto scan failed: {error}")
        self._reset_auto_scan_ui()

    def _reset_auto_scan_ui(self):
        self._cancel_btn.setVisible(False)
        self._select_btn.setEnabled(True)
        self._start_btn.setEnabled(True)
        self._auto_scan_btn.setEnabled(True)

    # ------------------------------------------------------------------

    def set_has_results(self, has_results: bool):
        self._back_btn.setVisible(has_results)

    def _append_log(self, text: str):
        self._log.append(text)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )
