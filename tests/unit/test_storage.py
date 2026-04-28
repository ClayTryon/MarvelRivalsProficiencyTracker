import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
import sqlite3
from storage.database import Database
from storage.repository import HeroRepository, CaptureRunRepository
from models.hero import Hero
from models.capture_run import CaptureStatus


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.connect()
    database.init_schema()
    return database


@pytest.fixture
def run_repo(db):
    return CaptureRunRepository(db)


@pytest.fixture
def hero_repo(db):
    return HeroRepository(db)


def make_hero(capture_run_id, name="Iron Man", level=5, xp=100, xp_required=400):
    return Hero(
        name=name,
        role="Duelist",
        level=level,
        xp=xp,
        xp_required=xp_required,
        is_max_level=False,
        capture_run_id=capture_run_id,
        updated_at="2026-04-18T12:00:00",
    )


def test_init_schema_creates_tables(db):
    cursor = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "hero" in tables
    assert "capture_run" in tables


def test_create_capture_run(run_repo):
    run = run_repo.create()
    assert run.id is not None
    assert run.status == CaptureStatus.RUNNING


def test_update_capture_run_status(run_repo):
    run = run_repo.create()
    run_repo.update_status(run.id, CaptureStatus.COMPLETED, hero_count=3)
    updated = run_repo.get_latest()
    assert updated.status == CaptureStatus.COMPLETED
    assert updated.hero_count == 3
    assert updated.completed_at is not None


def test_upsert_inserts_new_hero(run_repo, hero_repo):
    run = run_repo.create()
    hero = make_hero(run.id)
    hero_repo.upsert(hero)
    heroes = hero_repo.get_all()
    assert len(heroes) == 1
    assert heroes[0].name == "Iron Man"


def test_upsert_updates_existing_hero(run_repo, hero_repo):
    run1 = run_repo.create()
    hero_repo.upsert(make_hero(run1.id, level=5, xp=100))

    run2 = run_repo.create()
    hero_repo.upsert(make_hero(run2.id, level=10, xp=200))

    heroes = hero_repo.get_all()
    assert len(heroes) == 1
    assert heroes[0].level == 10
    assert heroes[0].xp == 200


def test_get_all_returns_heroes_ordered_by_name(run_repo, hero_repo):
    run = run_repo.create()
    for name in ["Thor", "Adam Warlock", "Black Panther"]:
        hero_repo.upsert(make_hero(run.id, name=name))
    names = [h.name for h in hero_repo.get_all()]
    assert names == sorted(names)


def test_cascade_delete_removes_heroes(db, run_repo, hero_repo):
    run = run_repo.create()
    hero_repo.upsert(make_hero(run.id))
    assert len(hero_repo.get_all()) == 1

    db.conn.execute("DELETE FROM capture_run WHERE id = ?", (run.id,))
    db.conn.commit()
    assert len(hero_repo.get_all()) == 0


def test_get_by_name(run_repo, hero_repo):
    run = run_repo.create()
    hero_repo.upsert(make_hero(run.id, name="Captain America"))
    found = hero_repo.get_by_name("Captain America")
    assert found is not None
    assert found.name == "Captain America"


def test_get_by_name_missing_returns_none(hero_repo):
    assert hero_repo.get_by_name("Nobody") is None
