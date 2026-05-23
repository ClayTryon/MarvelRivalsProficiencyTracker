"""QThread workers so RAG operations never block the UI thread."""
from PyQt6.QtCore import QThread, pyqtSignal


class QueryWorker(QThread):
    finished = pyqtSignal(str, list)   # answer text, list of source URLs
    error = pyqtSignal(str)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self._query = query

    def run(self):
        try:
            from rag.query_engine import get_engine
            engine = get_engine()
            response = engine.query(self._query)
            sources = sorted({
                node.metadata.get("url", "")
                for node in response.source_nodes
                if node.metadata.get("url")
            })
            self.finished.emit(str(response), sources)
        except Exception as exc:
            self.error.emit(str(exc))
