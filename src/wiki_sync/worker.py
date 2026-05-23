from PyQt6.QtCore import QThread, pyqtSignal
from wiki_sync.avatar_sync import parse_avatars_page, sync_icons, write_heroes_py
from wiki_sync.ability_scraper import sync_abilities, scrape_teamups

_WIKI_BASE = "https://marvelrivals.fandom.com/wiki/"


class SyncWorker(QThread):
    progress = pyqtSignal(int, int, str)   # current, total, message
    finished = pyqtSignal(dict)            # result summary dict
    error    = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(0, 1, "Fetching Avatars page from wiki...")
            icon_sets = parse_avatars_page()
            self.progress.emit(
                0, len(icon_sets),
                f"Found {len(icon_sets)} icon sets. Resolving download URLs...",
            )
            result = sync_icons(icon_sets, progress_cb=self._relay_progress)

            self.progress.emit(0, 1, "Updating heroes.py from wiki roster...")
            hero_count = write_heroes_py(icon_sets)
            result["heroes_written"] = hero_count

            self.progress.emit(0, 1, "Fetching hero abilities from wiki...")
            ab_result = sync_abilities(icon_sets, progress_cb=self._relay_progress)
            result["abilities_fetched"] = ab_result["fetched"]
            result["abilities_skipped"] = ab_result["skipped"]
            if ab_result["errors"]:
                result["errors"].extend(ab_result["errors"])

            tu_result = scrape_teamups(progress_cb=self._relay_progress)
            if tu_result["errors"]:
                result["errors"].extend(tu_result["errors"])

            # Build hero wiki URLs and rebuild the RAG index
            hero_urls = [
                _WIKI_BASE + s["wiki_page"].replace(" ", "_")
                for s in icon_sets
                if s.get("is_primary") and s.get("wiki_page")
            ]
            rag_total = len(hero_urls)
            self.progress.emit(0, rag_total, "Building RAG index from hero wiki pages...")
            try:
                from rag.ingest import rebuild_index
                rag_counter = [0]

                def _rag_cb(msg: str):
                    if "Fetching:" in msg:
                        rag_counter[0] += 1
                    self.progress.emit(rag_counter[0], rag_total, msg)

                rag_chunks = rebuild_index(hero_urls, progress_cb=_rag_cb)
                result["rag_chunks"] = rag_chunks
            except Exception as exc:
                result["errors"].append(f"RAG index: {exc}")
                result["rag_chunks"] = 0

            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

    def _relay_progress(self, current: int, total: int, msg: str):
        self.progress.emit(current, total, msg)
