from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt
from wiki_sync.worker import SyncWorker


class FirstRunDialog(QDialog):
    """Shown on first launch when no heroes.json exists. Auto-runs wiki sync."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProfTracker — First Run Setup")
        self.setFixedSize(480, 220)
        # Window flag gives it a taskbar button so it's findable
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet("background: #0c0c14; color: #e0e0e0;")
        self.raise_()
        self.activateWindow()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel("SETTING UP PROFTRACKER")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 16px; letter-spacing: 3px; color: #f4d641;"
        )
        lay.addWidget(title)

        self._status = QLabel("Connecting to Marvel Rivals wiki...")
        self._status.setStyleSheet("color: #aaa; font-size: 12px;")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(0)  # indeterminate until we know total
        self._bar.setFixedHeight(8)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            "QProgressBar { background: #1a1a2c; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background: #f4d641; border-radius: 4px; }"
        )
        lay.addWidget(self._bar)

        self._skip_btn = QPushButton("Skip (use built-in roster)")
        self._skip_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #484860;"
            " border: 1px solid #26263c; border-radius: 3px;"
            " font-size: 11px; padding: 4px 12px; }"
            "QPushButton:hover { color: #aaa; border-color: #aaa; }"
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

    def _on_finished(self, _result: dict):
        self.accept()

    def _on_error(self, msg: str):
        self._status.setText(f"Sync failed: {msg}\nUsing built-in roster.")
        self._bar.setMaximum(1)
        self._bar.setValue(1)
        self._skip_btn.setText("Continue")

    def _skip(self):
        self._worker.terminate()
        self.reject()
