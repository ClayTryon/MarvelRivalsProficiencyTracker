"""RAG-powered Hero Wiki panel — WIKI tab in ProfTracker."""
import json
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextBrowser, QSizePolicy,
)
from rag.worker import QueryWorker

_GOLD = "#f4d641"
_BG   = "#0c0c14"
_PANEL = "#141420"
_TEXT  = "#c8c8e0"
_DIM   = "#484860"
_ERR   = "#c84040"

_MAX_HISTORY = 40  # max Q&A items to persist across sessions

if getattr(sys, 'frozen', False):
    _CHAT_HISTORY_PATH = os.path.join(os.path.dirname(sys.executable), 'chat_history.json')
else:
    _CHAT_HISTORY_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "chat_history.json")
    )


class HeroInfoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")

        self._query_worker: QueryWorker | None = None
        self._history: list[dict] = []  # {"role", "body", "sources"?}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── title ────────────────────────────────────────────────────────────
        title = QLabel("HERO WIKI  —  RAG Knowledge Base")
        title.setStyleSheet(
            f"font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 15px; letter-spacing: 3px; color: {_GOLD};"
        )
        root.addWidget(title)

        disclaimer = QLabel(
            "Powered by Groq AI (free tier) — API key is shared. "
            "Please don't abuse it or it will be disabled for everyone."
        )
        disclaimer.setStyleSheet(f"color: {_DIM}; font-size: 10px; font-style: italic;")
        disclaimer.setWordWrap(True)
        root.addWidget(disclaimer)

        # ── status row ───────────────────────────────────────────────────────
        status_row = QHBoxLayout()

        self._status_label = QLabel("No pages indexed — run Wiki Sync to build index.")
        self._status_label.setStyleSheet(f"color: {_DIM}; font-size: 11px;")
        status_row.addWidget(self._status_label)
        status_row.addStretch()

        self._clear_btn = QPushButton("Clear Index")
        self._clear_btn.setFixedHeight(26)
        self._clear_btn.setStyleSheet(self._btn_style(_ERR, "#1a0000"))
        self._clear_btn.clicked.connect(self._clear_index)
        status_row.addWidget(self._clear_btn)

        root.addLayout(status_row)

        # ── chat history ─────────────────────────────────────────────────────
        self._chat = QTextBrowser()
        self._chat.setOpenExternalLinks(False)
        self._chat.setOpenLinks(False)
        self._chat.setStyleSheet(
            f"background: {_PANEL}; color: {_TEXT}; font-size: 13px;"
            " border: 1px solid #1a1a2c; border-radius: 4px; padding: 10px;"
        )
        self._chat.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self._chat, stretch=1)

        # ── query row ────────────────────────────────────────────────────────
        query_row = QHBoxLayout()
        query_row.setSpacing(8)

        self._query_input = QLineEdit()
        self._query_input.setPlaceholderText("Ask a question about any hero...")
        self._query_input.setStyleSheet(self._input_style())
        self._query_input.returnPressed.connect(self._send_query)
        query_row.addWidget(self._query_input)

        self._ask_btn = QPushButton("Ask")
        self._ask_btn.setFixedHeight(32)
        self._ask_btn.setStyleSheet(self._btn_style(_GOLD, "#1a1a00"))
        self._ask_btn.clicked.connect(self._send_query)
        query_row.addWidget(self._ask_btn)

        root.addLayout(query_row)

        self._refresh_status()
        self._load_history()

        try:
            from rag.ingest import rag_enabled
            if not rag_enabled():
                self._status_label.setText("RAG disabled (PROFTRACKER_DISABLE_RAG is set).")
                self._ask_btn.setEnabled(False)
                self._query_input.setEnabled(False)
        except Exception:
            pass

    # ── style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _input_style() -> str:
        return (
            f"QLineEdit {{"
            f" background: {_PANEL}; color: {_TEXT};"
            f" border: 1px solid #2a2a40; border-radius: 4px;"
            f" padding: 6px 10px; font-size: 12px;"
            f"}}"
            f" QLineEdit:focus {{ border-color: {_GOLD}; }}"
        )

    @staticmethod
    def _btn_style(fg: str, bg: str) -> str:
        return (
            f"QPushButton {{"
            f" background: {bg}; color: {fg}; border: 1px solid {fg};"
            f" border-radius: 4px; padding: 0 14px; font-size: 12px; font-weight: bold;"
            f"}}"
            f" QPushButton:hover {{ background: {fg}; color: #000000; }}"
            f" QPushButton:disabled {{ opacity: 0.35; }}"
        )

    # ── history persistence ───────────────────────────────────────────────────

    def _load_history(self):
        try:
            with open(_CHAT_HISTORY_PATH, encoding="utf-8") as f:
                items = json.load(f)
        except (FileNotFoundError, Exception):
            return
        for item in items:
            role = item.get("role", "")
            body = item.get("body", "")
            if role == "WIKI BOT":
                self._append_answer(body, item.get("sources", []))
            elif role:
                self._append(role, body)
        self._history = list(items)

    def _save_history(self):
        try:
            recent = self._history[-_MAX_HISTORY:]
            with open(_CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
                json.dump(recent, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── internal helpers ──────────────────────────────────────────────────────

    def _refresh_status(self):
        try:
            from rag.ingest import index_chunk_count
            n = index_chunk_count()
            self._status_label.setText(
                f"{n} chunk(s) indexed." if n else "No pages indexed — run Wiki Sync to build index."
            )
        except Exception:
            self._status_label.setText("Index unavailable.")

    def _set_busy(self, busy: bool):
        for w in (self._ask_btn, self._query_input):
            w.setEnabled(not busy)

    def _append(self, role: str, body: str, color: str = _TEXT):
        safe = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br/>")
        html = (
            f'<p style="margin:6px 0;">'
            f'<b style="color:{_GOLD};">{role}</b><br/>'
            f'<span style="color:{color};">{safe}</span>'
            f'</p>'
            f'<hr style="border:none;border-top:1px solid #1a1a2c;margin:4px 0;"/>'
        )
        self._chat.append(html)
        self._chat.verticalScrollBar().setValue(
            self._chat.verticalScrollBar().maximum()
        )

    def _append_answer(self, answer: str, sources: list[str]):
        safe = (
            answer.replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace("\n", "<br/>")
        )
        src_html = ""
        if sources:
            links = " &nbsp;|&nbsp; ".join(
                f'<a href="{s}" style="color:{_GOLD};">{s}</a>' for s in sources
            )
            src_html = f'<br/><small style="color:{_DIM};">Sources: {links}</small>'
        html = (
            f'<p style="margin:6px 0;">'
            f'<b style="color:{_GOLD};">WIKI BOT</b><br/>'
            f'<span style="color:{_TEXT};">{safe}</span>'
            f'{src_html}'
            f'</p>'
            f'<hr style="border:none;border-top:1px solid #1a1a2c;margin:4px 0;"/>'
        )
        self._chat.append(html)
        self._chat.verticalScrollBar().setValue(
            self._chat.verticalScrollBar().maximum()
        )

    # ── query ─────────────────────────────────────────────────────────────────

    def set_query(self, text: str):
        self._query_input.setText(text)
        self._query_input.setFocus()

    def _send_query(self):
        query = self._query_input.text().strip()
        if not query:
            return
        if len(query) > 500:
            self._append("ERROR", "Query too long (500 character limit).", color=_ERR)
            return
        self._query_input.clear()
        self._set_busy(True)
        self._status_label.setText("Querying…")
        self._append("YOU", query)
        self._history.append({"role": "YOU", "body": query})

        self._query_worker = QueryWorker(query, parent=self)
        self._query_worker.finished.connect(self._on_query_done)
        self._query_worker.error.connect(self._on_error)
        self._query_worker.start()

    def _on_query_done(self, answer: str, sources: list[str]):
        self._set_busy(False)
        self._refresh_status()
        self._append_answer(answer, sources)
        self._history.append({"role": "WIKI BOT", "body": answer, "sources": sources})
        self._save_history()
        self._query_input.setFocus()

    # ── clear ─────────────────────────────────────────────────────────────────

    def _clear_index(self):
        from rag.ingest import clear_index
        clear_index()
        self._chat.clear()
        self._history = []
        self._save_history()
        self._refresh_status()
        self._append("SYSTEM", "Index cleared.")

    # ── error ─────────────────────────────────────────────────────────────────

    def _on_error(self, msg: str):
        self._set_busy(False)
        self._append("ERROR", msg, color=_ERR)
        self._query_input.setFocus()
