import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS capture_run (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT    NOT NULL,
    completed_at  TEXT,
    status        TEXT    NOT NULL DEFAULT 'running'
                          CHECK(status IN ('running', 'completed', 'cancelled', 'failed')),
    hero_count    INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS hero (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    role           TEXT    NOT NULL,
    level          INTEGER NOT NULL CHECK(level >= 1),
    xp             INTEGER NOT NULL CHECK(xp >= 0),
    xp_required    INTEGER NOT NULL CHECK(xp_required >= 0),
    is_max_level   INTEGER NOT NULL DEFAULT 0 CHECK(is_max_level IN (0, 1)),
    capture_run_id INTEGER NOT NULL REFERENCES capture_run(id) ON DELETE CASCADE,
    updated_at     TEXT    NOT NULL,
    ch1_progress   REAL    NOT NULL DEFAULT 0,
    ch2_progress   REAL    NOT NULL DEFAULT 0,
    ch3_progress   REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS hero_snapshot (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    hero_name      TEXT    NOT NULL,
    capture_run_id INTEGER NOT NULL REFERENCES capture_run(id) ON DELETE CASCADE,
    level          INTEGER NOT NULL,
    xp             INTEGER NOT NULL,
    xp_required    INTEGER NOT NULL,
    is_max_level   INTEGER NOT NULL DEFAULT 0,
    recorded_at    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hero_capture_run ON hero(capture_run_id);
CREATE INDEX IF NOT EXISTS idx_hero_name ON hero(name);
CREATE INDEX IF NOT EXISTS idx_snapshot_hero ON hero_snapshot(hero_name);
CREATE INDEX IF NOT EXISTS idx_snapshot_time ON hero_snapshot(recorded_at);

CREATE TABLE IF NOT EXISTS tracker_stats (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    hero_name        TEXT    NOT NULL,
    username         TEXT    NOT NULL,
    season           INTEGER NOT NULL DEFAULT 0,
    mode             TEXT    NOT NULL DEFAULT 'all',
    matches_played   REAL,
    matches_won      REAL,
    win_pct          REAL,
    time_played_secs INTEGER,
    kda_ratio        REAL,
    kills            REAL,
    deaths           REAL,
    assists          REAL,
    mvp              REAL,
    svp              REAL,
    damage           REAL,
    healing          REAL,
    damage_blocked   REAL,
    hit_rate         REAL,
    fetched_at       TEXT    NOT NULL,
    UNIQUE(hero_name, username, season, mode)
);

CREATE TABLE IF NOT EXISTS tracker_seasons (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    short_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_tracker_hero ON tracker_stats(hero_name);

CREATE TABLE IF NOT EXISTS match_history (
    match_uid     TEXT    NOT NULL,
    username      TEXT    NOT NULL,
    played_at     TEXT,
    duration_secs REAL,
    map_id        INTEGER,
    season        TEXT,
    game_mode_id  INTEGER,
    result        TEXT,
    is_mvp        INTEGER NOT NULL DEFAULT 0,
    is_svp        INTEGER NOT NULL DEFAULT 0,
    hero_id       INTEGER,
    hero_name     TEXT,
    kills         REAL,
    deaths        REAL,
    assists       REAL,
    damage        REAL,
    healing       REAL,
    damage_taken  REAL,
    score_delta   REAL,
    fetched_at    TEXT    NOT NULL,
    PRIMARY KEY (match_uid, username)
);

CREATE INDEX IF NOT EXISTS idx_match_played  ON match_history(played_at);
CREATE INDEX IF NOT EXISTS idx_match_user    ON match_history(username);
CREATE INDEX IF NOT EXISTS idx_match_hero    ON match_history(hero_name);
"""


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    def init_schema(self):
        for statement in _SCHEMA.split(";"):
            statement = statement.strip()
            if statement:
                self.conn.execute(statement)
        self.conn.commit()

    def migrate_schema(self):
        """Add columns/tables introduced after initial release (safe to call repeatedly)."""
        new_cols = [
            ("tracker_stats", "time_played_secs", "INTEGER"),
            ("tracker_stats", "healing",          "REAL"),
            ("tracker_stats", "healing_per_min",  "REAL"),
            ("tracker_stats", "damage_blocked",   "REAL"),
        ]
        for table, col, col_type in new_cols:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except Exception:
                pass  # column already exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tracker_seasons (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, short_name TEXT
            )
        """)
        for col, col_type in [
            ("hero_id",   "INTEGER"),
            ("hero_name", "TEXT"),
            ("map_id",    "INTEGER"),
            ("game_mode_id", "INTEGER"),
            ("score_delta",  "REAL"),
        ]:
            try:
                self.conn.execute(
                    f"ALTER TABLE match_history ADD COLUMN {col} {col_type}"
                )
            except Exception:
                pass  # column already exists or table schema differs
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_match_played ON match_history(played_at)",
            "CREATE INDEX IF NOT EXISTS idx_match_user   ON match_history(username)",
            "CREATE INDEX IF NOT EXISTS idx_match_hero   ON match_history(hero_name)",
        ]:
            self.conn.execute(idx_sql)
        for col in ["ch1_progress", "ch2_progress", "ch3_progress"]:
            try:
                self.conn.execute(f"ALTER TABLE hero ADD COLUMN {col} REAL NOT NULL DEFAULT 0")
            except Exception:
                pass
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
