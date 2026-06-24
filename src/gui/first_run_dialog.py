from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
)
from PyQt6.QtCore import Qt
from wiki_sync.worker import SyncWorker
from gui.colors import (
    BG_APP, BORDER, BORDER_MID,
    TEXT_DIM, TEXT_LIGHT_GRAY, TEXT_DIALOG,
    GOLD,
)


class FirstRunDialog(QDialog):
    """Shown on first launch when no heroes.json exists. Auto-runs CDN sync."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProfTracker — First Run Setup")
        self.setFixedSize(480, 210)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet(f"background: {BG_APP}; color: {TEXT_DIALOG};")
        self.raise_()
        self.activateWindow()
        self._build_ui()
        self._start_worker()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel("SETTING UP PROFTRACKER")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 16px; letter-spacing: 3px; color: {GOLD};"
        )
        lay.addWidget(title)

        self._status = QLabel("Downloading hero data from server...")
        self._status.setStyleSheet(f"color: {TEXT_LIGHT_GRAY}; font-size: 12px;")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(0)
        self._bar.setFixedHeight(8)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            f"QProgressBar {{ background: {BORDER_MID}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {GOLD}; border-radius: 4px; }}"
        )
        lay.addWidget(self._bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setStyleSheet(
            f"QPushButton {{ background: {GOLD}; color: #000;"
            f" border: none; border-radius: 3px;"
            f" font-size: 11px; font-weight: bold; padding: 4px 16px; }}"
            f"QPushButton:hover {{ background: #ffd966; }}"
        )
        self._retry_btn.clicked.connect(self._retry)
        self._retry_btn.hide()
        btn_row.addWidget(self._retry_btn)

        self._skip_btn = QPushButton("Skip (use built-in roster)")
        self._skip_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_DIM};"
            f" border: 1px solid {BORDER}; border-radius: 3px;"
            f" font-size: 11px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ color: {TEXT_LIGHT_GRAY}; border-color: {TEXT_LIGHT_GRAY}; }}"
        )
        self._skip_btn.clicked.connect(self._skip)
        btn_row.addWidget(self._skip_btn)

        lay.addLayout(btn_row)

    def _start_worker(self):
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

    def _on_finished(self, _result: dict):
        self.accept()

    def _on_error(self, msg: str):
        self._status.setText(
            "Could not reach the data server. This is usually a temporary AWS outage "
            "or a network issue.\n\nPlease try again later, or continue with the "
            "built-in roster (hero icons and abilities won't be available until you sync)."
        )
        self._bar.setMaximum(1)
        self._bar.setValue(0)
        self._retry_btn.show()
        self._skip_btn.setText("Continue without syncing")

    def _retry(self):
        self._retry_btn.hide()
        self._skip_btn.setText("Skip (use built-in roster)")
        self._status.setText("Retrying...")
        self._bar.setMaximum(0)
        self._bar.setValue(0)
        self._start_worker()

    def _skip(self):
        self._worker.stop()
        self._worker.wait(3000)
        self.reject()
