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
    updated_at     TEXT    NOT NULL
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

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
