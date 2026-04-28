import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from models.hero import Hero
from exceptions import ValidationError


def make_hero(**kwargs):
    defaults = dict(
        name="Iron Man",
        role="Duelist",
        level=5,
        xp=100,
        xp_required=400,
        is_max_level=False,
        capture_run_id=1,
        updated_at="2026-04-18T12:00:00",
    )
    defaults.update(kwargs)
    return Hero(**defaults)


def test_valid_hero_passes():
    h = make_hero()
    h.validate()  # should not raise


def test_empty_name_raises():
    h = make_hero(name="")
    with pytest.raises(ValidationError):
        h.validate()


def test_whitespace_name_raises():
    h = make_hero(name="   ")
    with pytest.raises(ValidationError):
        h.validate()


def test_level_zero_raises():
    h = make_hero(level=0)
    with pytest.raises(ValidationError):
        h.validate()


def test_negative_level_raises():
    h = make_hero(level=-1)
    with pytest.raises(ValidationError):
        h.validate()


def test_negative_xp_raises():
    h = make_hero(xp=-1)
    with pytest.raises(ValidationError):
        h.validate()


def test_max_level_with_nonzero_xp_required_raises():
    h = make_hero(is_max_level=True, xp=0, xp_required=400)
    with pytest.raises(ValidationError):
        h.validate()


def test_max_level_with_zero_xp_required_passes():
    h = make_hero(is_max_level=True, xp=0, xp_required=0)
    h.validate()


def test_xp_gte_xp_required_when_not_max_raises():
    h = make_hero(is_max_level=False, xp=400, xp_required=400)
    with pytest.raises(ValidationError):
        h.validate()


def test_xp_exceeds_xp_required_raises():
    h = make_hero(is_max_level=False, xp=500, xp_required=400)
    with pytest.raises(ValidationError):
        h.validate()


def test_progress_pct_max_level_is_zero():
    h = make_hero(is_max_level=True, xp=0, xp_required=0)
    assert h.progress_pct == 0.0


def test_progress_pct_normal():
    h = make_hero(xp=44, xp_required=400)
    assert abs(h.progress_pct - 11.0) < 0.01


def test_progress_pct_large_values():
    h = make_hero(xp=2452081, xp_required=3000000)
    expected = 2452081 / 3000000 * 100
    assert abs(h.progress_pct - expected) < 0.01
