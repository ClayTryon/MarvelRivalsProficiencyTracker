from datetime import datetime, timezone, timedelta
from models.hero import Hero
from models.capture_run import CaptureRun, CaptureStatus
from storage.database import Database


class CaptureRunRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self) -> CaptureRun:
        started_at = datetime.now(timezone.utc).isoformat()
        cursor = self.db.conn.execute(
            "INSERT INTO capture_run (started_at, status) VALUES (?, ?)",
            (started_at, CaptureStatus.RUNNING.value),
        )
        self.db.conn.commit()
        return CaptureRun(id=cursor.lastrowid, started_at=started_at, status=CaptureStatus.RUNNING)

    def update_status(self, run_id: int, status: CaptureStatus, hero_count: int = None, error_message: str = None):
        completed_at = datetime.now(timezone.utc).isoformat() if status != CaptureStatus.RUNNING else None
        self.db.conn.execute(
            """UPDATE capture_run
               SET status = ?, completed_at = ?,
                   hero_count = COALESCE(?, hero_count),
                   error_message = COALESCE(?, error_message)
               WHERE id = ?""",
            (status.value, completed_at, hero_count, error_message, run_id),
        )
        self.db.conn.commit()

    def get_latest(self) -> CaptureRun | None:
        row = self.db.conn.execute(
            "SELECT * FROM capture_run ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._row_to_run(row) if row else None

    def _row_to_run(self, row) -> CaptureRun:
        return CaptureRun(
            id=row["id"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            status=CaptureStatus(row["status"]),
            hero_count=row["hero_count"],
            error_message=row["error_message"],
        )


class HeroRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, hero: Hero):
        self.db.conn.execute(
            """INSERT INTO hero (name, role, level, xp, xp_required, is_max_level, capture_run_id, updated_at,
                                 ch1_progress, ch2_progress, ch3_progress)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 role = excluded.role,
                 level = excluded.level,
                 xp = excluded.xp,
                 xp_required = excluded.xp_required,
                 is_max_level = excluded.is_max_level,
                 capture_run_id = excluded.capture_run_id,
                 updated_at = excluded.updated_at,
                 ch1_progress = excluded.ch1_progress,
                 ch2_progress = excluded.ch2_progress,
                 ch3_progress = excluded.ch3_progress""",
            (
                hero.name, hero.role, hero.level, hero.xp, hero.xp_required,
                1 if hero.is_max_level else 0,
                hero.capture_run_id, hero.updated_at,
                hero.ch1_progress, hero.ch2_progress, hero.ch3_progress,
            ),
        )
        self.db.conn.commit()

    def get_all(self) -> list[Hero]:
        rows = self.db.conn.execute(
            "SELECT * FROM hero ORDER BY name ASC"
        ).fetchall()
        return [self._row_to_hero(r) for r in rows]

    def get_by_name(self, name: str) -> Hero | None:
        row = self.db.conn.execute(
            "SELECT * FROM hero WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_hero(row) if row else None

    def _row_to_hero(self, row) -> Hero:
        keys = row.keys()
        return Hero(
            id=row["id"],
            name=row["name"],
            role=row["role"],
            level=row["level"],
            xp=row["xp"],
            xp_required=row["xp_required"],
            is_max_level=bool(row["is_max_level"]),
            capture_run_id=row["capture_run_id"],
            updated_at=row["updated_at"],
            ch1_progress=float(row["ch1_progress"]) if "ch1_progress" in keys else 0.0,
            ch2_progress=float(row["ch2_progress"]) if "ch2_progress" in keys else 0.0,
            ch3_progress=float(row["ch3_progress"]) if "ch3_progress" in keys else 0.0,
        )


class SnapshotRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert(self, hero: Hero):
        self.db.conn.execute(
            """INSERT INTO hero_snapshot
               (hero_name, capture_run_id, level, xp, xp_required, is_max_level, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                hero.name, hero.capture_run_id, hero.level, hero.xp, hero.xp_required,
                1 if hero.is_max_level else 0,
                hero.updated_at,
            ),
        )
        self.db.conn.commit()

    def backfill_from_heroes(self):
        """Insert a snapshot for any hero that has no snapshot for its current capture_run_id."""
        self.db.conn.execute(
            """INSERT INTO hero_snapshot
               (hero_name, capture_run_id, level, xp, xp_required, is_max_level, recorded_at)
               SELECT h.name, h.capture_run_id, h.level, h.xp, h.xp_required, h.is_max_level, h.updated_at
               FROM hero h
               WHERE NOT EXISTS (
                   SELECT 1 FROM hero_snapshot s
                   WHERE s.hero_name = h.name AND s.capture_run_id = h.capture_run_id
               )"""
        )
        self.db.conn.commit()

    def get_xp_velocity(self, hero_name: str, days: int = 14) -> float | None:
        """Average XP/day for a hero over the last N days; None if insufficient data."""
        from data.xp_table import total_xp_earned
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self.db.conn.execute(
            """SELECT recorded_at, level, xp FROM hero_snapshot
               WHERE hero_name = ? AND recorded_at >= ?
               ORDER BY recorded_at ASC""",
            (hero_name, cutoff),
        ).fetchall()
        if len(rows) < 2:
            return None
        first, last = rows[0], rows[-1]
        xp_gained = total_xp_earned(last["level"], last["xp"]) - total_xp_earned(first["level"], first["xp"])
        first_dt = datetime.fromisoformat(first["recorded_at"])
        last_dt  = datetime.fromisoformat(last["recorded_at"])
        elapsed  = (last_dt - first_dt).total_seconds() / 86400
        if elapsed < 0.01 or xp_gained <= 0:
            return None
        return xp_gained / elapsed

    def get_xp_history(self, days: int | None) -> dict[str, list[tuple[datetime, int]]]:
        from data.xp_table import total_xp_earned
        if days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            rows = self.db.conn.execute(
                """SELECT hero_name, recorded_at, level, xp
                   FROM hero_snapshot
                   WHERE recorded_at >= ?
                   ORDER BY hero_name, recorded_at""",
                (cutoff,),
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                """SELECT hero_name, recorded_at, level, xp
                   FROM hero_snapshot
                   ORDER BY hero_name, recorded_at"""
            ).fetchall()

        result: dict[str, list[tuple[datetime, int, int]]] = {}
        for row in rows:
            dt = datetime.fromisoformat(row["recorded_at"]).replace(tzinfo=None)
            total_xp = total_xp_earned(row["level"], row["xp"])
            result.setdefault(row["hero_name"], []).append((dt, total_xp, row["level"]))
        return result


class TrackerRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, uid: str, season: int, mode: str, hero_name: str, stats: dict):
        now = datetime.now(timezone.utc).isoformat()
        self.db.conn.execute(
            """INSERT INTO tracker_stats
               (hero_name, username, season, mode,
                matches_played, matches_won, win_pct,
                time_played_secs, kda_ratio, kills, deaths, assists,
                mvp, svp, damage, healing, damage_blocked, hit_rate,
                fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(hero_name, username, season, mode) DO UPDATE SET
                 matches_played   = excluded.matches_played,
                 matches_won      = excluded.matches_won,
                 win_pct          = excluded.win_pct,
                 time_played_secs = excluded.time_played_secs,
                 kda_ratio        = excluded.kda_ratio,
                 kills            = excluded.kills,
                 deaths           = excluded.deaths,
                 assists          = excluded.assists,
                 mvp              = excluded.mvp,
                 svp              = excluded.svp,
                 damage           = excluded.damage,
                 healing          = excluded.healing,
                 damage_blocked   = excluded.damage_blocked,
                 hit_rate         = excluded.hit_rate,
                 fetched_at       = excluded.fetched_at""",
            (
                hero_name, uid, season, mode,
                stats.get("matches_played"), stats.get("matches_won"), stats.get("win_pct"),
                stats.get("time_played_secs"), stats.get("kda_ratio"),
                stats.get("kills"), stats.get("deaths"), stats.get("assists"),
                stats.get("mvp"), stats.get("svp"),
                stats.get("damage"), stats.get("healing"), stats.get("damage_blocked"),
                stats.get("hit_rate"),
                now,
            ),
        )
        self.db.conn.commit()

    def get_stats_for_mode(self, uid: str | None, season: int, mode: str) -> dict[str, dict]:
        """Return per-hero stats for the given mode.

        season=0 means no season filter (all stored data).
        mode='all'     → aggregate ranked + unranked (sum additive fields, recalc derived)
        mode='ranked'  → only ranked rows
        mode='unranked'→ only unranked rows
        """
        season_clause = "" if season == 0 else "AND season=?"
        uid_clause    = "AND username=?" if uid else ""

        def _season_params(base: tuple) -> tuple:
            return base + ((season,) if season else ()) + ((uid,) if uid else ())

        if mode == "all":
            params = _season_params(())
            rows = self.db.conn.execute(
                f"""SELECT
                      hero_name,
                      SUM(matches_played)   AS matches_played,
                      SUM(matches_won)      AS matches_won,
                      CASE WHEN SUM(matches_played) > 0
                           THEN CAST(SUM(matches_won) AS REAL) / SUM(matches_played) * 100
                           ELSE NULL END    AS win_pct,
                      SUM(time_played_secs) AS time_played_secs,
                      SUM(kills)            AS kills,
                      SUM(deaths)           AS deaths,
                      SUM(assists)          AS assists,
                      CASE WHEN SUM(deaths) > 0
                           THEN (SUM(kills) + SUM(assists)) / CAST(SUM(deaths) AS REAL)
                           ELSE (SUM(kills) + SUM(assists)) END AS kda_ratio,
                      SUM(damage)           AS damage,
                      SUM(healing)          AS healing,
                      SUM(damage_blocked)   AS damage_blocked,
                      CASE WHEN SUM(COALESCE(matches_played, 0)) > 0
                           THEN SUM(COALESCE(hit_rate, 0) * COALESCE(matches_played, 0))
                                / SUM(COALESCE(matches_played, 0))
                           ELSE NULL END    AS hit_rate
                   FROM tracker_stats
                   WHERE 1=1 {season_clause} {uid_clause}
                   GROUP BY hero_name
                   ORDER BY matches_played DESC""",
                params,
            ).fetchall()
        else:
            params = _season_params((mode,))
            if uid:
                rows = self.db.conn.execute(
                    f"SELECT * FROM tracker_stats WHERE mode=? {season_clause} {uid_clause}"
                    " ORDER BY matches_played DESC",
                    params,
                ).fetchall()
            else:
                rows = self.db.conn.execute(
                    f"SELECT * FROM tracker_stats WHERE mode=? {season_clause}"
                    " ORDER BY matches_played DESC",
                    params,
                ).fetchall()
        return {r["hero_name"]: dict(r) for r in rows}


class MatchHistoryRepository:
    def __init__(self, db: Database):
        self.db = db

    def purge_other_users(self, keep_username: str):
        self.db.conn.execute(
            "DELETE FROM match_history WHERE username != ?", (keep_username,)
        )
        self.db.conn.execute(
            "DELETE FROM tracker_stats WHERE username != ?", (keep_username,)
        )
        self.db.conn.commit()

    def get_newest_match_uid(self, username: str) -> str | None:
        row = self.db.conn.execute(
            "SELECT match_uid FROM match_history WHERE username=?"
            " ORDER BY played_at DESC LIMIT 1",
            (username,),
        ).fetchone()
        return row["match_uid"] if row else None

    def upsert_match(self, username: str, match: dict):
        from tracker.client import hero_name as resolve_name
        now = datetime.now(timezone.utc).isoformat()
        hero_id = match.get("hero_id")
        hero_nm = resolve_name(int(hero_id)) if hero_id is not None else None
        self.db.conn.execute(
            """INSERT OR IGNORE INTO match_history
               (match_uid, username, played_at, duration_secs, map_id, season,
                game_mode_id, result, is_mvp, is_svp,
                hero_id, hero_name, kills, deaths, assists,
                damage, healing, damage_taken, score_delta, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match["match_uid"], username, match.get("played_at"),
                match.get("duration_secs"), match.get("map_id"), match.get("season"),
                match.get("game_mode_id"), match.get("result"),
                1 if match.get("is_mvp") else 0,
                1 if match.get("is_svp") else 0,
                hero_id, hero_nm,
                match.get("kills"), match.get("deaths"), match.get("assists"),
                match.get("damage"), match.get("healing"), match.get("damage_taken"),
                match.get("score_delta"),
                now,
            ),
        )
        self.db.conn.commit()

    def clear_match_history(self, username: str):
        self.db.conn.execute("DELETE FROM match_history WHERE username=?", (username,))
        self.db.conn.commit()

    def get_match_count(self, username: str) -> int:
        row = self.db.conn.execute(
            "SELECT COUNT(*) FROM match_history WHERE username=?", (username,)
        ).fetchone()
        return row[0] if row else 0


def seed_default_heroes(db: Database) -> int:
    """Populate the hero table with every roster entry at level 1, xp 0.

    Creates a dedicated seed capture_run to satisfy the FK constraint.
    Skips any hero that already has a row (safe to call multiple times).
    Returns the number of heroes inserted.
    """
    from data.heroes import HERO_ROSTER, HERO_ROLES
    from data.xp_table import XP_PER_LEVEL
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.conn.execute(
        "INSERT INTO capture_run (started_at, status, hero_count) VALUES (?, 'completed', ?)",
        (now, len(HERO_ROSTER)),
    )
    db.conn.commit()
    run_id = cursor.lastrowid

    repo = HeroRepository(db)
    count = 0
    for name in HERO_ROSTER:
        if repo.get_by_name(name) is None:
            hero = Hero(
                name=name,
                role=HERO_ROLES.get(name, "Unknown"),
                level=1,
                xp=0,
                xp_required=XP_PER_LEVEL[1],
                is_max_level=False,
                capture_run_id=run_id,
                updated_at=now,
            )
            hero.validate()
            repo.upsert(hero)
            count += 1
    return count
