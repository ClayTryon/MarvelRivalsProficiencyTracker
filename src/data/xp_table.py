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

_XP_TO_RANGE: dict[int, tuple[int, int]] = {
    xp: (lo, hi) for lo, hi, xp in _RANGES
}

# Cumulative XP required to REACH each level (i.e. total earned before that level starts)
_XP_TO_REACH: dict[int, int] = {}
_cumulative = 0
for _lo, _hi, _xp in _RANGES:
    for _lvl in range(_lo, _hi + 1):
        _XP_TO_REACH[_lvl] = _cumulative
        _cumulative += _xp

TOTAL_XP_FOR_CHAMPION: int = _XP_TO_REACH[50]  # 54,100


def total_xp_earned(level: int, current_xp: int) -> int:
    return _XP_TO_REACH.get(level, 0) + current_xp


def xp_for_level(level: int) -> int | None:
    return XP_PER_LEVEL.get(level)


def level_range_for_xp(xp_required: int) -> tuple[int, int] | None:
    """Return the (lo, hi) level range that corresponds to xp_required, or None."""
    return _XP_TO_RANGE.get(xp_required)


def fit_level_to_range(ocr_level: int, lo: int, hi: int) -> tuple[int, bool]:
    """Fit an OCR'd level into the valid range [lo, hi].

    If already in range, returns as-is.
    Tries stripping a spurious leading '1' (e.g. '17' → '7' when range is 5-9).
    Tries prepending a '1' (e.g. '7' → '17' when range is 15-19).
    Falls back to clamping to the nearest edge of the range.
    """
    if lo <= ocr_level <= hi:
        return ocr_level, False

    s = str(ocr_level)

    # Strip spurious leading '1' (e.g. 17 → 7, 11 → 1)
    if s.startswith('1') and len(s) > 1:
        candidate = int(s[1:])
        if lo <= candidate <= hi:
            return candidate, True

    # Prepend missing '1' (e.g. 7 → 17, 5 → 15)
    candidate = int('1' + s)
    if lo <= candidate <= hi:
        return candidate, True

    # Clamp to nearest range boundary
    clamped = max(lo, min(ocr_level, hi))
    return clamped, True
