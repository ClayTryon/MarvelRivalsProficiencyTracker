"""
XP and level tables for Marvel Rivals hero proficiency.

Levels are grouped into bands that share the same XP-per-level value.
The tables are built once at import time and used for OCR cross-validation
and UI progress calculations.
"""

_RANGES = [
    (1,  4,  125),
    (5,  9,  240),
    (10, 14, 400),
    (15, 19, 480),
    (20, 49, 1600),
    (50, 70, 3100),
]

XP_PER_LEVEL: dict[int, int] = {
    level: xp
    for lo, hi, xp in _RANGES
    for level in range(lo, hi + 1)
}

# Maps xp_required value → (lo, hi) level band — used to cross-validate OCR'd levels
_XP_TO_RANGE: dict[int, tuple[int, int]] = {
    xp: (lo, hi) for lo, hi, xp in _RANGES
}

# Cumulative XP required to reach each level (total earned before that level starts)
_XP_TO_REACH: dict[int, int] = {}
_cumulative = 0
for _lo, _hi, _xp in _RANGES:
    for _lvl in range(_lo, _hi + 1):
        _XP_TO_REACH[_lvl] = _cumulative
        _cumulative += _xp

TOTAL_XP_FOR_CHAMPION: int = _XP_TO_REACH[50]  # 54,100


def total_xp_earned(level: int, current_xp: int) -> int:
    """Total XP earned across all levels including current progress."""
    return _XP_TO_REACH.get(level, 0) + current_xp


def level_range_for_xp(xp_required: int) -> tuple[int, int] | None:
    """Return the (lo, hi) level band that has this xp_required value, or None."""
    return _XP_TO_RANGE.get(xp_required)


def fit_level_to_range(ocr_level: int, lo: int, hi: int) -> tuple[int, bool]:
    """Fit an OCR'd level into the valid range [lo, hi].

    Tries common look-alike corrections before falling back to clamping:
    - Strip spurious leading '1' (e.g. '17' → '7' when range is 5–9)
    - Prepend missing '1'   (e.g. '7'  → '17' when range is 15–19)
    Returns (corrected_level, was_corrected).
    """
    if lo <= ocr_level <= hi:
        return ocr_level, False

    s = str(ocr_level)

    if s.startswith('1') and len(s) > 1:
        candidate = int(s[1:])
        if lo <= candidate <= hi:
            return candidate, True

    candidate = int('1' + s)
    if lo <= candidate <= hi:
        return candidate, True

    clamped = max(lo, min(ocr_level, hi))
    return clamped, True
