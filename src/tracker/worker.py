import time

from PyQt6.QtCore import QThread, pyqtSignal

from tracker.client import fetch_hero_stats, fetch_all_match_history
from storage.database import Database
from storage.repository import MatchHistoryRepository, TrackerRepository


class TrackerWorker(QThread):
    progress  = pyqtSignal(int, int, str)
    finished  = pyqtSignal(int)
    cancelled = pyqtSignal()
    error     = pyqtSignal(str)

    def __init__(self, uid: str, season: int, db: Database, parent=None):
        super().__init__(parent)
        self._uid      = uid
        self._season   = season
        self._db_path  = db.db_path

    def run(self):
        db = Database(self._db_path)
        db.connect()
        try:
            MatchHistoryRepository(db).purge_other_users(self._uid)
            t_repo = TrackerRepository(db)

            def _retry_cb(wait_secs: int, attempt: int):
                self.progress.emit(0, 0, f"Rate limited — retrying in {wait_secs}s (attempt {attempt})…")

            # ── Phase 1: aggregated hero stats ────────────────────────────
            if self._season == 0:
                # Probe seasons 1, 2, 3, … stopping after 3 consecutive empty results
                total_entries = 0
                empty_streak  = 0
                season_num    = 1
                while season_num <= 60:
                    if self.isInterruptionRequested():
                        self.cancelled.emit()
                        return
                    self.progress.emit(0, 0, f"Fetching season {season_num} hero stats…")
                    try:
                        pools = fetch_hero_stats(self._uid, season_num, retry_cb=_retry_cb)
                        hero_count = sum(len(v) for v in pools.values())
                    except Exception as e:
                        self.progress.emit(0, 0, f"Season {season_num} failed ({e}), skipping…")
                        hero_count = 0

                    if hero_count == 0:
                        empty_streak += 1
                        if empty_streak >= 3:
                            break
                    else:
                        empty_streak = 0
                        for mode, hero_stats in pools.items():
                            for hero_name, stats in hero_stats.items():
                                t_repo.upsert(self._uid, season_num, mode, hero_name, stats)
                        total_entries += hero_count
                        self.progress.emit(
                            season_num, 0,
                            f"Season {season_num}: {hero_count} entries stored  (total {total_entries})…"
                        )

                    season_num += 1
                    time.sleep(0.4)

                self._last_season = season_num - 1
                self.progress.emit(1, 1, f"Hero stats stored ({total_entries} entries, checked {season_num - 1} seasons).")
            else:
                # Single explicit season
                self.progress.emit(0, 0, f"Fetching season {self._season} hero stats for {self._uid}…")
                try:
                    pools = fetch_hero_stats(self._uid, self._season, retry_cb=_retry_cb)
                    for mode, hero_stats in pools.items():
                        for hero_name, stats in hero_stats.items():
                            t_repo.upsert(self._uid, self._season, mode, hero_name, stats)
                    self.progress.emit(1, 1, f"Season {self._season} stats stored ({sum(len(v) for v in pools.values())} entries).")
                except Exception as e:
                    self.progress.emit(0, 0, f"Hero stats fetch failed ({e}), continuing…")
                self._last_season = self._season

            if self.isInterruptionRequested():
                self.cancelled.emit()
                return

            # ── Phase 2: match history — one fetch per season ────────────
            match_repo = MatchHistoryRepository(db)
            stored     = 0

            seasons_to_fetch = range(1, self._last_season + 1) if self._season == 0 else [self._season]

            for s in seasons_to_fetch:
                if self.isInterruptionRequested():
                    self.cancelled.emit()
                    return

                # Per-season stop: skip matches already stored for this season
                row = db.conn.execute(
                    "SELECT match_uid FROM match_history WHERE username=? AND season=?"
                    " ORDER BY played_at DESC LIMIT 1",
                    (self._uid, str(s)),
                ).fetchone()
                stop_uid = row["match_uid"] if row else None

                self.progress.emit(stored, 0, f"Fetching season {s} match history…")

                def _store_page(page: list[dict], _s=s):
                    nonlocal stored
                    for match in page:
                        match_repo.upsert_match(self._uid, match)
                        stored += 1
                    self.progress.emit(stored, 0, f"S{_s}: stored {stored} matches total…")

                fetch_all_match_history(
                    self._uid,
                    season=s,
                    stop_at_uid=stop_uid,
                    delay=1.0,
                    page_cb=_store_page,
                    cancel_check=self.isInterruptionRequested,
                )
                time.sleep(0.5)

            if self.isInterruptionRequested():
                self.cancelled.emit()
                return

            if stored == 0:
                self.progress.emit(1, 1, "Match history already up to date.")

            self.finished.emit(stored)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            db.close()
