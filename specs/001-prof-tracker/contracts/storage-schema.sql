-- ProfTracker Storage Schema
-- SQLite DDL contract
-- Database file: proficiency_tracker.db

PRAGMA foreign_keys = ON;

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

CREATE INDEX IF NOT EXISTS idx_hero_capture_run ON hero(capture_run_id);
CREATE INDEX IF NOT EXISTS idx_hero_name ON hero(name);
