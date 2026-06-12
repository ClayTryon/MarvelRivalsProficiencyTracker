"""QThread workers so RAG operations never block the UI thread."""
import random
import time

from PyQt6.QtCore import QThread, pyqtSignal


class QueryWorker(QThread):
    finished = pyqtSignal(str, list)   # answer text, list of source URLs
    error = pyqtSignal(str)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self._query = query

    def run(self):
        try:
            from rag.ingest import rag_enabled
            if not rag_enabled():
                self.error.emit("RAG is disabled (PROFTRACKER_DISABLE_RAG is set).")
                return
            from rag.query_engine import get_engine
            engine = get_engine()
            response = self._query_with_retry(engine)
            sources = sorted({
                node.metadata.get("url", "")
                for node in response.source_nodes
                if node.metadata.get("url")
            })
            self.finished.emit(str(response), sources)
        except Exception as exc:
            self.error.emit(str(exc))

    def _query_with_retry(self, engine, max_retries: int = 3):
        delay = 1.0
        for attempt in range(max_retries):
            try:
                return engine.query(self._query)
            except Exception as exc:
                is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                if is_rate_limit and attempt < max_retries - 1:
                    sleep_for = delay + random.uniform(0, delay)
                    time.sleep(sleep_for)
                    delay *= 2
                    continue
                raise
