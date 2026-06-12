from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QPlainTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from wiki_sync.worker import SyncWorker


class SyncPanel(QWidget):
    sync_complete = pyqtSignal()

    _BTN = (
        "QPushButton {"
        " background: #f4d641; color: #1a1a1a; border: none;"
        " border-radius: 4px; font-size: 13px; font-weight: bold;"
        " letter-spacing: 1px; padding: 8px 28px;"
        "}"
        "QPushButton:hover { background: #ffe066; }"
        "QPushButton:disabled { background: #2a2a3a; color: #555; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("WIKI SYNC")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 20px; letter-spacing: 4px; color: #f4d641;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "Downloads Hero, Lord, and Champion icons for every hero\n"
            "from the Marvel Rivals Fandom wiki.\n"
            "Icons already present in the Icons folder are skipped."
        )
        desc.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        self._sync_btn = QPushButton("SYNC FROM WIKI")
        self._sync_btn.setStyleSheet(self._BTN)
        self._sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_btn.clicked.connect(self._start_sync)
        btn_row.addWidget(self._sync_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: #1a1a2c; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background: #f4d641; border-radius: 4px; }"
        )
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self._status)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "QPlainTextEdit {"
            " background: #080810; color: #ccc;"
            " font-family: Consolas, 'Courier New', monospace;"
            " font-size: 11px; border: 1px solid #1a1a2c;"
            " border-radius: 4px;"
            "}"
        )
        layout.addWidget(self._log)

        self._worker: SyncWorker | None = None

    def _start_sync(self):
        self._sync_btn.setEnabled(False)
        self._log.clear()
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(1)
        self._progress_bar.show()
        self._status.setText("Connecting to wiki...")

        self._worker = SyncWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, msg: str):
        self._progress_bar.setMaximum(max(total, 1))
        self._progress_bar.setValue(current)
        self._status.setText(msg)
        self._log.appendPlainText(f"[{current}/{total}] {msg}")

    def _on_finished(self, result: dict):
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._sync_btn.setEnabled(True)

        d = result["downloaded"]
        s = result["skipped"]
        e = result["errors"]
        h = result.get("heroes_written", 0)
        af = result.get("abilities_fetched", 0)
        ask = result.get("abilities_skipped", 0)
        rag = result.get("rag_chunks", 0)
        added = result.get("heroes_added", 0)
        summary = (
            f"Done — {d} icons downloaded, {s} skipped | "
            f"{h} heroes in roster | "
            f"{af} ability files fetched, {ask} skipped | "
            f"{rag} RAG chunks indexed"
        )
        if e:
            summary += f", {len(e)} error(s)"
            for err in e:
                self._log.appendPlainText(f"  ERROR: {err}")

        if added > 0:
            self._log.appendPlainText(
                f"\n⚡ {added} new hero(es) added to the roster since last sync. "
                "Run a scan to capture their proficiency data."
            )

        self._status.setText(summary)
        self._log.appendPlainText(f"\n{summary}")
        self.sync_complete.emit()

    def _on_error(self, msg: str):
        self._sync_btn.setEnabled(True)
        self._progress_bar.hide()
        self._status.setText(f"Error: {msg}")
        self._log.appendPlainText(f"FATAL ERROR: {msg}")
