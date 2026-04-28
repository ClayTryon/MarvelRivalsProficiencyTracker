from datetime import datetime, timezone
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
