from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QLineEdit,
)
from PyQt6.QtCore import Qt, QSettings
from wiki_sync.worker import SyncWorker
from gui.colors import (
    BG_APP, BG_INPUT, BORDER, BORDER_MID, BORDER_INPUT,
    TEXT, TEXT_DIM, TEXT_LIGHT_GRAY, TEXT_DIALOG,
    GOLD, GRAY_66,
)


class FirstRunDialog(QDialog):
    """Shown on first launch when no heroes.json exists. Auto-runs wiki sync."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProfTracker — First Run Setup")
        self.setFixedSize(480, 270)
        # Window flag gives it a taskbar button so it's findable
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet(f"background: {BG_APP}; color: {TEXT_DIALOG};")
        self.raise_()
        self.activateWindow()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel("SETTING UP PROFTRACKER")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 16px; letter-spacing: 3px; color: {GOLD};"
        )
        lay.addWidget(title)

        self._status = QLabel("Connecting to Marvel Rivals wiki...")
        self._status.setStyleSheet(f"color: {TEXT_LIGHT_GRAY}; font-size: 12px;")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        # Optional rivalsmeta UID — saved to QSettings for auto-refresh
        uid_row = QHBoxLayout()
        uid_lbl = QLabel("rivalsmeta player UID")
        uid_lbl.setStyleSheet(f"color: {GRAY_66}; font-size: 11px;")
        uid_row.addWidget(uid_lbl)
        self._ign_input = QLineEdit()
        self._ign_input.setPlaceholderText("optional — numeric ID from rivalsmeta.com")
        self._ign_input.setStyleSheet(
            f"QLineEdit {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER_INPUT};"
            f" border-radius: 3px; padding: 3px 8px; font-size: 11px; }}"
            f" QLineEdit:focus {{ border-color: {GOLD}; }}"
        )
        saved_uid = QSettings("ProfTracker", "HeroBrowser").value("tracker_uid", "")
        self._ign_input.setText(saved_uid)
        uid_row.addWidget(self._ign_input, stretch=1)
        lay.addLayout(uid_row)

        sub_lbl = QLabel("Your stats will auto-sync every launch via the STATS tab.")
        sub_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        lay.addWidget(sub_lbl)

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(0)  # indeterminate until we know total
        self._bar.setFixedHeight(8)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            f"QProgressBar {{ background: {BORDER_MID}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {GOLD}; border-radius: 4px; }}"
        )
        lay.addWidget(self._bar)

        self._skip_btn = QPushButton("Skip (use built-in roster)")
        self._skip_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_DIM};"
            f" border: 1px solid {BORDER}; border-radius: 3px;"
            f" font-size: 11px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ color: {TEXT_LIGHT_GRAY}; border-color: {TEXT_LIGHT_GRAY}; }}"
        )
        self._skip_btn.clicked.connect(self._skip)
        lay.addWidget(self._skip_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._worker = SyncWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, msg: str):
        if total > 0:
            self._bar.setMaximum(total)
            self._bar.setValue(current)
        self._status.setText(msg)

    def _save_ign(self):
        uid = self._ign_input.text().strip()
        if uid:
            QSettings("ProfTracker", "HeroBrowser").setValue("tracker_uid", uid)

    def _on_finished(self, _result: dict):
        self._save_ign()
        self.accept()

    def _on_error(self, msg: str):
        self._status.setText(f"Sync failed: {msg}\nUsing built-in roster.")
        self._bar.setMaximum(1)
        self._bar.setValue(1)
        self._skip_btn.setText("Continue")

    def _skip(self):
        self._save_ign()
        self._worker.stop()
        self._worker.wait(3000)
        self.reject()
