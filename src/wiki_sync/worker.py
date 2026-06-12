import json
import os
import threading

from PyQt6.QtCore import QThread, pyqtSignal
from wiki_sync.avatar_sync import (
    CDN_BASE,
    heroes_json_path,
    parse_avatars_page,
    sync_from_cdn,
    sync_icons,
    update_release_dates,
    write_heroes_py,
)
from wiki_sync.ability_scraper import (
    fetch_release_dates,
    scrape_teamups,
    sync_abilities,
    sync_abilities_from_cdn,
)

_WIKI_BASE = "https://marvelrivals.fandom.com/wiki/"


class SyncWorker(QThread):
    progress = pyqtSignal(int, int, str)   # current, total, message
    finished = pyqtSignal(dict)            # result summary dict
    error    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            if CDN_BASE:
                self._run_cdn_sync()
            else:
                self._run_wiki_sync()
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_wiki_sync(self):
        self.progress.emit(0, 1, "Fetching Avatars page from wiki...")
        icon_sets = parse_avatars_page()
        self.progress.emit(
            0, len(icon_sets),
            f"Found {len(icon_sets)} icon sets. Resolving download URLs...",
        )
        result = sync_icons(icon_sets, progress_cb=self._relay_progress)

        self.progress.emit(0, 1, "Updating heroes.py from wiki roster...")
        from data.heroes import HERO_ROSTER
        prev_count = len(HERO_ROSTER)
        hero_count = write_heroes_py(icon_sets)
        result["heroes_written"] = hero_count
        result["heroes_added"] = max(0, hero_count - prev_count)

        self.progress.emit(0, 1, "Fetching hero abilities from wiki...")
        ab_result = sync_abilities(icon_sets, progress_cb=self._relay_progress)
        result["abilities_fetched"] = ab_result["fetched"]
        result["abilities_skipped"] = ab_result["skipped"]
        if ab_result["errors"]:
            result["errors"].extend(ab_result["errors"])

        tu_result = scrape_teamups(progress_cb=self._relay_progress)
        if tu_result["errors"]:
            result["errors"].extend(tu_result["errors"])

        self.progress.emit(0, 1, "Fetching hero release dates...")
        release_dates = fetch_release_dates(icon_sets, progress_cb=self._relay_progress)
        update_release_dates(release_dates)

        self._rebuild_rag(icon_sets, result)
        self.finished.emit(result)

    def _run_cdn_sync(self):
        self.progress.emit(0, 1, f"Syncing hero data from CDN ({CDN_BASE})...")
        result: dict = {"errors": [], "heroes_added": 0}

        icon_result = sync_from_cdn(progress_cb=self._relay_progress)
        result["downloaded"] = icon_result["downloaded"]
        result["skipped"] = icon_result["skipped"]
        result["heroes_written"] = icon_result["heroes_written"]
        result["errors"].extend(icon_result["errors"])

        # Derive slug list from the freshly downloaded heroes.json
        with open(heroes_json_path(), encoding="utf-8") as f:
            heroes_data = json.load(f)
        roster: list[str] = heroes_data.get("roster", [])
        slugs = [n.replace(" ", "_").replace("&", "%26") for n in roster]

        self.progress.emit(0, 1, "Downloading abilities from CDN...")
        ab_result = sync_abilities_from_cdn(slugs, progress_cb=self._relay_progress)
        result["abilities_fetched"] = ab_result["fetched"]
        result["abilities_skipped"] = ab_result["skipped"]
        result["errors"].extend(ab_result["errors"])

        # RAG index is always rebuilt locally (wiki URLs are still used for content)
        icon_sets_stub = [
            {
                "is_primary": True,
                "wiki_page": n,
                "slug": s,
            }
            for n, s in zip(roster, slugs)
        ]
        self.progress.emit(0, 1, "Rebuilding RAG index...")
        self._rebuild_rag(icon_sets_stub, result)
        self.finished.emit(result)

    def _rebuild_rag(self, icon_sets: list[dict], result: dict) -> None:
        from rag.ingest import rag_enabled, rebuild_index
        if not rag_enabled():
            self.progress.emit(0, 1, "RAG disabled — skipping index build.")
            result["rag_chunks"] = 0
            return
        hero_urls = [
            _WIKI_BASE + s["wiki_page"].replace(" ", "_")
            for s in icon_sets
            if s.get("is_primary") and s.get("wiki_page")
        ]
        rag_total = len(hero_urls)
        self.progress.emit(0, rag_total, "Building RAG index from hero wiki pages...")
        try:
            rag_counter = [0]

            def _rag_cb(msg: str):
                if "Fetching:" in msg:
                    rag_counter[0] += 1
                self.progress.emit(rag_counter[0], rag_total, msg)

            result["rag_chunks"] = rebuild_index(hero_urls, progress_cb=_rag_cb)
        except Exception as exc:
            result.setdefault("errors", []).append(f"RAG index: {exc}")
            result["rag_chunks"] = 0

    def _relay_progress(self, current: int, total: int, msg: str):
        if self._stop_event.is_set():
            raise InterruptedError("sync cancelled")
        self.progress.emit(current, total, msg)
