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
            """INSERT INTO hero (name, role, level, xp, xp_required, is_max_level, capture_run_id, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 role = excluded.role,
                 level = excluded.level,
                 xp = excluded.xp,
                 xp_required = excluded.xp_required,
                 is_max_level = excluded.is_max_level,
                 capture_run_id = excluded.capture_run_id,
                 updated_at = excluded.updated_at""",
            (
                hero.name, hero.role, hero.level, hero.xp, hero.xp_required,
                1 if hero.is_max_level else 0,
                hero.capture_run_id, hero.updated_at,
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
