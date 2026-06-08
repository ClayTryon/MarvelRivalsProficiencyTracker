import json
import time
import urllib.error
import urllib.parse
import urllib.request

_BASE = "https://rivalsmeta.com/api"

_HERO_NAMES: dict[int, str] = {
    1011: "Hulk",
    1014: "The Punisher",
    1015: "Storm",
    1016: "Loki",
    1017: "Human Torch",
    1018: "Doctor Strange",
    1020: "Mantis",
    1021: "Hawkeye",
    1022: "Captain America",
    1023: "Rocket Raccoon",
    1024: "Hela",
    1025: "Cloak & Dagger",
    1026: "Black Panther",
    1027: "Groot",
    1028: "Ultron",
    1029: "Magik",
    1030: "Moon Knight",
    1031: "Luna Snow",
    1032: "Squirrel Girl",
    1033: "Black Widow",
    1034: "Iron Man",
    1035: "Venom",
    1036: "Spider-Man",
    1037: "Magneto",
    1038: "Scarlet Witch",
    1039: "Thor",
    1040: "Mister Fantastic",
    1041: "Winter Soldier",
    1042: "Peni Parker",
    1043: "Star-Lord",
    1044: "Blade",
    1045: "Namor",
    1046: "Adam Warlock",
    1047: "Jeff the Land Shark",
    1048: "Psylocke",
    1049: "Wolverine",
    1050: "Invisible Woman",
    1051: "The Thing",
    1052: "Iron Fist",
    1053: "Emma Frost",
    1054: "Phoenix",
    1055: "Daredevil",
    1056: "Angela",
    1058: "Gambit",
    1059: "Elsa Bloodstone",
    1060: "White Fox",
    1061: "Black Cat",
    1062: "Devil Dinosaur",
    1065: "Rogue",
    # Deadpool has three role variants — all map to the same hero
    10571: "Deadpool",
    10572: "Deadpool",
    10573: "Deadpool",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://rivalsmeta.com/",
}


def hero_name(hero_id: int) -> str:
    return _HERO_NAMES.get(hero_id, f"Hero_{hero_id}")


def _fetch(url: str, retries: int = 4, retry_cb=None) -> object:
    delay = 15
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                retry_after = exc.headers.get("Retry-After")
                wait = max(delay, int(retry_after)) if retry_after else delay
                if retry_cb:
                    retry_cb(wait, attempt + 1)
                time.sleep(wait)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


# ── Hero stats ─────────────────────────────────────────────────────────────────

def _extract_stats(s: dict) -> dict:
    cnt = s.get("main_attack_cnt") or 0
    hit = s.get("main_attack_hit") or 0
    k   = s.get("kills")   or 0
    d   = s.get("deaths")  or 0
    a   = s.get("assists") or 0
    m   = s.get("matches") or 0
    w   = s.get("win")     or 0
    return {
        "matches_played":    m,
        "matches_won":       w,
        "win_pct":           (w / m * 100) if m else None,
        "kda_ratio":         ((k + a) / d) if d else ((k + a) or None),
        "kills":             k,
        "deaths":            d,
        "assists":           a,
        "time_played_secs":  int(s.get("play_time") or 0),
        "damage":            s.get("damage"),
        "healing":           s.get("heal"),
        "damage_blocked":    s.get("damage_taken"),
        "mvp":               s.get("mvp"),
        "svp":               s.get("svp"),
        "hit_rate":          (hit / cnt) if cnt > 0 else None,
        "_attack_cnt":       cnt,
        "_attack_hit":       hit,
    }


def _merge_stats(a: dict, b: dict) -> dict:
    """Sum two hero stat dicts (used when a hero appears under multiple role IDs)."""
    additive = [
        "matches_played", "matches_won", "kills", "deaths", "assists",
        "time_played_secs", "damage", "healing", "damage_blocked",
        "mvp", "svp", "_attack_cnt", "_attack_hit",
    ]
    merged = dict(a)
    for key in additive:
        av = a.get(key) or 0
        bv = b.get(key) or 0
        merged[key] = av + bv
    m  = merged["matches_played"]
    w  = merged["matches_won"]
    k  = merged["kills"]
    d  = merged["deaths"]
    aa = merged["assists"]
    cnt = merged["_attack_cnt"]
    hit = merged["_attack_hit"]
    merged["win_pct"]    = (w / m * 100) if m else None
    merged["kda_ratio"]  = ((k + aa) / d) if d else ((k + aa) or None)
    merged["hit_rate"]   = (hit / cnt) if cnt > 0 else None
    return merged


def _parse_hero_pool(raw: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for hero_id_str, s in raw.items():
        name  = hero_name(int(hero_id_str))
        stats = _extract_stats(s)
        if name in result:
            result[name] = _merge_stats(result[name], stats)
        else:
            result[name] = stats
    return result


def fetch_hero_stats(uid: str, season: int = 0, retry_cb=None) -> dict[str, dict[str, dict]]:
    """Fetch aggregated hero stats.

    Returns {"ranked": {hero_name: stats}, "unranked": {hero_name: stats}}.
    season=0 means no season filter (all-time career).
    """
    url = f"{_BASE}/player/{urllib.parse.quote(str(uid), safe='')}"
    if season:
        url += f"?season={season}"
    data = _fetch(url, retry_cb=retry_cb)
    return {
        "ranked":   _parse_hero_pool(data.get("heroes_ranked",   {})),
        "unranked": _parse_hero_pool(data.get("heroes_unranked", {})),
    }


# ── Match history ──────────────────────────────────────────────────────────────

def _parse_match(raw: dict) -> dict | None:
    match_uid = raw.get("match_uid")
    if not match_uid:
        return None

    mp  = raw.get("match_player") or {}        # player-specific block
    ph  = mp.get("player_hero") or {}           # per-hero stats for this player
    df  = mp.get("dynamic_fields") or {}        # score/level change

    ts  = raw.get("match_time_stamp")
    uid = mp.get("player_uid")
    return {
        "match_uid":      match_uid,
        "played_at":      str(ts) if ts else None,
        "duration_secs":  raw.get("match_play_duration"),
        "map_id":         raw.get("match_map_id"),
        "season":         raw.get("match_season"),
        "game_mode_id":   raw.get("game_mode_id"),
        "result":         "win" if mp.get("is_win") else "loss",
        "is_mvp":         uid is not None and uid == raw.get("mvp_uid"),
        "is_svp":         uid is not None and uid == raw.get("svp_uid"),
        "hero_id":        ph.get("hero_id"),
        "kills":          ph.get("k"),
        "deaths":         ph.get("d"),
        "assists":        ph.get("a"),
        "damage":         ph.get("total_hero_damage"),
        "healing":        ph.get("total_hero_heal"),
        "damage_taken":   ph.get("total_damage_taken"),
        "score_delta":    df.get("add_score"),
    }


def fetch_match_history_page(
    uid: str,
    skip: int = 0,
    game_mode_id: int = 0,
    hero_id: int = 0,
    season: int = 0,
) -> list[dict]:
    params = f"skip={skip}&game_mode_id={game_mode_id}&hero_id={hero_id}"
    if season:
        params += f"&season={season}"
    url = f"{_BASE}/player-match-history/{urllib.parse.quote(str(uid), safe='')}?{params}"
    data = _fetch(url)
    if not isinstance(data, list):
        return []
    return [m for raw in data if (m := _parse_match(raw)) is not None]


def fetch_all_match_history(
    uid: str,
    season: int = 0,
    stop_at_uid: str | None = None,
    delay: float = 1.5,
    page_cb=None,
    cancel_check=None,
) -> list[dict]:
    """Paginate through all match history, newest first.

    stop_at_uid: match_uid to stop at (exclusive) for incremental updates.
    page_cb(page: list[dict]) called with each page before sleeping.
    """
    matches: list[dict] = []
    skip = 0

    while True:
        page = fetch_match_history_page(uid, skip=skip, season=season)
        if not page:
            break

        batch: list[dict] = []
        done = False
        for m in page:
            if stop_at_uid and m["match_uid"] == stop_at_uid:
                done = True
                break
            batch.append(m)

        if batch and page_cb:
            page_cb(batch)
        matches.extend(batch)

        if done or len(page) < 20:
            break

        if cancel_check and cancel_check():
            break

        skip += 20
        time.sleep(delay)

    return matches


# ── Match detail (full 12-player scoreboard) ───────────────────────────────────

def fetch_match_detail(match_uid: str) -> dict:
    url = f"{_BASE}/matches/{urllib.parse.quote(match_uid, safe='')}"
    return _fetch(url)
