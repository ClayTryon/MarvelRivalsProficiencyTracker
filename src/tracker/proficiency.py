"""
Proficiency estimation from match history.

Simulates per-hero proficiency XP by replaying match history and counting
per-match challenge completions (ch1/ch2/ch3), multiplied by challenge point values.
"""

from data.xp_table import XP_PER_LEVEL

# game_mode_id values that count toward proficiency (QP=1, Competitive=2)
_PROFICIENCY_MODES = frozenset({1, 2})

# New system (rivalsmeta seasons 4+) point values
_NEW_CH1_PTS = 20        # permanent per-match reward for 15-min time challenge
_NEW_STAT_PTS: dict[str, int] = {
    "agent": 7, "knight": 13, "captain": 20, "centurion": 26, "lord": 80,
}

# Old system (rivalsmeta seasons 1–3) fixed per-challenge points
# Ch1 (60 min cumulative) and Ch4 (ability) are excluded — can't be tracked per-match
_OLD_STAT_PTS = 50


def _challenge_stat(row: dict, stat_type: str) -> float | None:
    if stat_type == "damage":
        return row.get("damage")
    if stat_type == "block":
        return row.get("damage_taken")
    if stat_type == "healing":
        return row.get("healing")
    if stat_type == "damage_healing":
        return (row.get("damage") or 0) + (row.get("healing") or 0) or None
    if stat_type in ("final_hits", "kos"):
        return row.get("kills")
    if stat_type == "kos_assists":
        return ((row.get("kills") or 0) + (row.get("assists") or 0)) or None
    return None


def estimate_mission_xp(uid: str, db) -> dict[str, dict]:
    """Simulate per-hero proficiency XP by replaying match history.

    Challenge progress (ch1/ch2/ch3) is persisted on the Hero object between calls so
    incremental runs continue from where they left off rather than starting from 0.
    Only matches newer than the hero's last processed match_uid are replayed.

    Arcade/other modes cap at ARCADE_DAILY_CAP pts per hero per day.
    Old system (seasons 1-3): Ch1=3600s, Ch2/Ch3=fixed thresholds, 60/50/50 pts.
    New system (seasons 4+):  Ch1=900s,  Ch2/Ch3=rank-scaled,       20/rank/rank pts.

    Returns {hero_name: {"total_pts", "sim_level", "ch1", "ch2", "ch3",
                          "tracked", "arcade_skip"}}
    """
    from collections import defaultdict
    from datetime import datetime, timezone
    from data.proficiency_missions import (
        PROFICIENCY_MISSIONS, OLD_PROFICIENCY_MISSIONS, OLD_SYSTEM_SEASONS, rank_for_level,
    )
    from data.xp_table import XP_PER_LEVEL
    from storage.repository import HeroRepository

    ARCADE_DAILY_CAP = 45
    _max_level = max(XP_PER_LEVEL.keys())

    hero_repo = HeroRepository(db)
    hero_objects = {h.name: h for h in hero_repo.get_all()}

    rows = db.conn.execute(
        """SELECT hero_name, season, game_mode_id, duration_secs,
                  damage, healing, damage_taken, kills, assists, played_at
           FROM match_history WHERE username = ?
           ORDER BY played_at ASC""",
        (uid,),
    ).fetchall()

    hero_matches: dict[str, list] = defaultdict(list)
    for row in rows:
        if row["hero_name"]:
            hero_matches[row["hero_name"]].append(row)

    result: dict[str, dict] = {}

    for hero_name, matches in hero_matches.items():
        hero_obj = hero_objects.get(hero_name)

        # Always simulate from level 1 — replays full match history in order
        level    = 1
        xp       = 0
        ch1_prog = 0.0
        ch2_prog = 0.0
        ch3_prog = 0.0

        total_pts = ch1_n = ch2_n = ch3_n = tracked = arcade_skip = 0
        arcade_daily: dict[tuple, float] = defaultdict(float)

        for row in matches:
            gm        = row["game_mode_id"]
            is_ranked = gm in _PROFICIENCY_MODES

            if not is_ranked:
                try:
                    day = datetime.fromtimestamp(int(row["played_at"]), tz=timezone.utc).date().isoformat()
                except (TypeError, ValueError):
                    arcade_skip += 1
                    continue
                if arcade_daily[(hero_name, day)] >= ARCADE_DAILY_CAP:
                    arcade_skip += 1
                    continue

            try:
                season_num = int(row["season"])
            except (TypeError, ValueError):
                arcade_skip += 1
                continue

            tracked += 1
            rank = rank_for_level(level)
            m    = dict(row)

            if season_num in OLD_SYSTEM_SEASONS:
                missions = OLD_PROFICIENCY_MISSIONS.get(hero_name)
                if not missions:
                    continue
                ch1_thresh = 3600.0
                ch2_thresh = float(missions["ch2_threshold"])
                ch3_thresh = float(missions["ch3_threshold"])
                ch1_pts, ch2_pts, ch3_pts = 60, _OLD_STAT_PTS, _OLD_STAT_PTS
            else:
                missions = PROFICIENCY_MISSIONS.get(hero_name)
                if not missions:
                    continue
                ch1_thresh = 900.0
                ch2_thresh = float(missions["ch2"][rank])
                ch3_thresh = float(missions["ch3"][rank])
                ch1_pts = _NEW_CH1_PTS
                ch2_pts = ch3_pts = _NEW_STAT_PTS[rank]

            # Accumulate this match's stats into running progress totals
            ch1_prog += row["duration_secs"] or 0
            v2 = _challenge_stat(m, missions["ch2_type"])
            v3 = _challenge_stat(m, missions["ch3_type"])
            if v2 is not None:
                ch2_prog += v2
            if v3 is not None:
                ch3_prog += v3

            # Award points for every full threshold crossed (carry-over triggers again)
            match_xp = 0
            while ch1_prog >= ch1_thresh:
                match_xp += ch1_pts
                ch1_n    += 1
                ch1_prog -= ch1_thresh
            while ch2_prog >= ch2_thresh:
                match_xp += ch2_pts
                ch2_n    += 1
                ch2_prog -= ch2_thresh
            while ch3_prog >= ch3_thresh:
                match_xp += ch3_pts
                ch3_n    += 1
                ch3_prog -= ch3_thresh

            # Arcade daily cap
            if not is_ranked and match_xp > 0:
                remaining  = ARCADE_DAILY_CAP - arcade_daily[(hero_name, day)]
                match_xp   = min(match_xp, remaining)
                arcade_daily[(hero_name, day)] += match_xp

            total_pts += match_xp
            xp        += match_xp

            # Level up after all points awarded
            while level < _max_level:
                needed = XP_PER_LEVEL.get(level, XP_PER_LEVEL[_max_level])
                if xp >= needed:
                    xp    -= needed
                    level += 1
                else:
                    break

        # Write progress back to Hero object and persist
        if hero_obj is not None:
            hero_obj.ch1_progress = ch1_prog
            hero_obj.ch2_progress = ch2_prog
            hero_obj.ch3_progress = ch3_prog
            try:
                hero_repo.upsert(hero_obj)
            except Exception:
                pass

        result[hero_name] = {
            "total_pts": total_pts,
            "sim_level": level,
            "ch1": ch1_n, "ch2": ch2_n, "ch3": ch3_n,
            "tracked":     tracked,
            "arcade_skip": arcade_skip,
        }

    return result
