"""
Parse the Marvel Rivals Fandom Avatars page and download Hero / Lord / Champion icons.

Icon filename convention (local Icons/ folder):
  Hero_Icon_{slug}.png
  Lord_Icon_{slug}.png
  Champion_Icon_{slug}_Animated.gif

where slug = hero_name.replace(" ", "_").replace("&", "%26"), derived from the
Lord icon filename (most consistent naming in the wikitext).
"""

import json
import logging
import os
import re
import sys
import time

import requests

log = logging.getLogger(__name__)

WIKI_API = "https://marvelrivals.fandom.com/api.php"

if getattr(sys, 'frozen', False):
    ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
else:
    ICONS_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Icons")
    )

_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "ProfTracker/4.0 (educational project)"

_REQUEST_DELAY = float(os.environ.get("PROFTRACKER_REQUEST_DELAY", "0.5"))

CDN_BASE = "https://proftracker-wiki-data-clayhtryon.s3.amazonaws.com"


def parse_avatars_page() -> list[dict]:
    """Fetch Avatars wikitext and return list of icon-set dicts."""
    resp = _SESSION.get(WIKI_API, params={
        "action": "parse", "page": "Avatars",
        "prop": "wikitext", "format": "json",
    }, timeout=20)
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]
    return _parse_wikitext(wikitext)


def _lord_slug(lord_file: str) -> str:
    """'Lord Icon Black Cat.png' → 'Black_Cat'"""
    name = lord_file.removeprefix("Lord Icon ").removesuffix(".png")
    return name.replace(" ", "_").replace("&", "%26")


def _parse_wikitext(wikitext: str) -> list[dict]:
    # Only the main table — stop before Costume Exclusive section
    main = wikitext.split("== Costume Exclusive Avatars ==")[0]
    rows = re.split(r'\n\s*\|-', main)

    icon_sets = []
    current_role = None

    for row in rows:
        # Track role as it changes (rowspan carries it across sub-form rows)
        all_roles = re.findall(
            r'\[\[File:(Vanguard|Duelist|Strategist) Icon\.png', row
        )
        if all_roles:
            current_role = "Multi-Role" if len(all_roles) > 1 else all_roles[0]

        # Extract all image filenames from this row
        all_files = re.findall(r'\[\[File:([^\|]+\.(?:png|gif))\|', row)

        hero_files = [
            f for f in all_files
            if f.startswith("Hero Icon") or "DEFAULT Table Icon" in f
        ]
        lord_files = [f for f in all_files if f.startswith("Lord Icon")]
        champ_files = [
            f for f in all_files
            if "Champion Icon" in f and "Animated" in f
        ]

        if lord_files and champ_files:
            slug = _lord_slug(lord_files[0])
            # Rows with a hero name link are primary forms; sub-form rows have no Teko span
            teko_match = re.search(
                r'font-family: Teko.*?\[\[([^\|\]]+)\|', row, re.DOTALL
            )
            is_primary = bool(teko_match)
            wiki_page = teko_match.group(1).strip() if teko_match else None
            icon_sets.append({
                "slug": slug,
                "role": current_role or "Unknown",
                "is_primary": is_primary,
                "wiki_page": wiki_page,
                "hero_wiki_file": hero_files[0] if hero_files else None,
                "lord_wiki_file": lord_files[0],
                "champion_wiki_file": champ_files[0],
                "hero_local": f"Hero_Icon_{slug}.png",
                "lord_local": f"Lord_Icon_{slug}.png",
                "champion_local": f"Champion_Icon_{slug}_Animated.gif",
            })

    return icon_sets


def _slug_to_name(slug: str) -> str:
    return slug.replace("_", " ").replace("%26", "&")


def _heroes_json_path() -> str:
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'heroes.json')
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'heroes.json')
    )


def heroes_json_path() -> str:
    """Public accessor for the heroes.json path used by server_sync and worker."""
    return _heroes_json_path()


def write_heroes_py(icon_sets: list[dict]) -> int:
    """Write hero roster to heroes.json next to the exe (or project root in dev)."""
    import json
    primary = sorted(
        [s for s in icon_sets if s["is_primary"]],
        key=lambda s: _slug_to_name(s["slug"]),
    )
    names = [_slug_to_name(s["slug"]) for s in primary]
    roles = {_slug_to_name(s["slug"]): s["role"] for s in primary}

    with open(_heroes_json_path(), 'w', encoding='utf-8') as f:
        json.dump({'roster': names, 'roles': roles}, f, indent=2, ensure_ascii=False)

    return len(names)


def resolve_cdn_urls(wiki_filenames: list[str]) -> dict[str, str]:
    """Batch-resolve wiki filenames to CDN download URLs via imageinfo API."""
    result: dict[str, str] = {}
    chunk_size = 30

    for i in range(0, len(wiki_filenames), chunk_size):
        chunk = wiki_filenames[i:i + chunk_size]
        titles = "|".join(f"File:{f}" for f in chunk)
        resp = _SESSION.get(WIKI_API, params={
            "action": "query", "titles": titles,
            "prop": "imageinfo", "iiprop": "url", "format": "json",
        }, timeout=20)
        resp.raise_for_status()

        for page in resp.json().get("query", {}).get("pages", {}).values():
            ii = page.get("imageinfo", [])
            if ii:
                title = page["title"].removeprefix("File:")
                result[title] = ii[0]["url"]

        if i + chunk_size < len(wiki_filenames):
            time.sleep(_REQUEST_DELAY)

    return result


def sync_icons(
    icon_sets: list[dict],
    progress_cb=None,
) -> dict:
    """
    Download icons for all icon_sets to ICONS_DIR.

    progress_cb(current: int, total: int, message: str) is called per hero.
    Returns {"downloaded": int, "skipped": int, "errors": list[str]}.
    """
    os.makedirs(ICONS_DIR, exist_ok=True)

    # Collect unique wiki filenames for batch URL resolution
    all_wiki_files: list[str] = []
    for s in icon_sets:
        if s["hero_wiki_file"]:
            all_wiki_files.append(s["hero_wiki_file"])
        all_wiki_files.append(s["lord_wiki_file"])
        all_wiki_files.append(s["champion_wiki_file"])
    all_wiki_files = list(dict.fromkeys(all_wiki_files))

    if progress_cb:
        progress_cb(0, len(icon_sets),
                    f"Resolving CDN URLs for {len(all_wiki_files)} files...")

    cdn_map = resolve_cdn_urls(all_wiki_files)

    downloaded = 0
    skipped = 0
    errors: list[str] = []

    for i, s in enumerate(icon_sets):
        pairs = [
            (s.get("hero_wiki_file"), s["hero_local"]),
            (s["lord_wiki_file"],     s["lord_local"]),
            (s["champion_wiki_file"], s["champion_local"]),
        ]
        for wiki_file, local_name in pairs:
            if not wiki_file:
                continue

            local_path = os.path.join(ICONS_DIR, local_name)
            if os.path.exists(local_path):
                skipped += 1
                continue

            cdn_url = cdn_map.get(wiki_file)
            if not cdn_url:
                errors.append(f"No CDN URL resolved: {wiki_file}")
                continue

            try:
                r = _SESSION.get(cdn_url, timeout=30, stream=True)
                if r.status_code == 429:
                    log.warning("HTTP 429 rate-limited fetching %s — skipping", local_name)
                    errors.append(f"{local_name}: HTTP 429 rate limited")
                    continue
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                downloaded += 1
                time.sleep(_REQUEST_DELAY)
            except Exception as exc:
                errors.append(f"{local_name}: {exc}")

        if progress_cb:
            hero_display = s["slug"].replace("_", " ").replace("%26", "&")
            progress_cb(i + 1, len(icon_sets), hero_display)

    return {"downloaded": downloaded, "skipped": skipped, "errors": errors}


def update_release_dates(release_dates: dict[str, str]) -> None:
    """Add or overwrite the release_dates field in the existing heroes.json."""
    path = _heroes_json_path()
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["release_dates"] = release_dates
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sync_from_cdn(progress_cb=None) -> dict:
    """
    Download heroes.json and icon files from PROFTRACKER_CDN_BASE instead of
    scraping the Fandom wiki. Called by SyncWorker when the env var is set.

    Returns {"downloaded": int, "skipped": int, "errors": list[str],
             "heroes_written": int}.
    """
    if not CDN_BASE:
        raise RuntimeError("PROFTRACKER_CDN_BASE is not set")

    os.makedirs(ICONS_DIR, exist_ok=True)
    errors: list[str] = []
    downloaded = skipped = 0

    # 1. Fetch heroes.json
    if progress_cb:
        progress_cb(0, 1, "Downloading heroes.json from CDN...")
    try:
        r = _SESSION.get(f"{CDN_BASE}/heroes.json", timeout=15)
        r.raise_for_status()
        heroes_data = r.json()
        with open(_heroes_json_path(), "w", encoding="utf-8") as f:
            json.dump(heroes_data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        raise RuntimeError(f"Failed to download heroes.json from CDN: {exc}") from exc

    # 2. Build icon filename list from roster
    roster: list[str] = heroes_data.get("roster", [])
    slugs = [n.replace(" ", "_").replace("&", "%26") for n in roster]
    icon_files: list[str] = []
    for slug in slugs:
        icon_files.append(f"Hero_Icon_{slug}.png")
        icon_files.append(f"Lord_Icon_{slug}.png")
        icon_files.append(f"Champion_Icon_{slug}_Animated.gif")

    # 3. Download icons
    total = len(icon_files)
    for i, filename in enumerate(icon_files):
        local_path = os.path.join(ICONS_DIR, filename)
        if os.path.exists(local_path):
            skipped += 1
            continue
        if progress_cb:
            progress_cb(i, total, f"Downloading {filename}...")
        try:
            r = _SESSION.get(f"{CDN_BASE}/icons/{filename}", timeout=30, stream=True)
            if r.status_code == 404:
                skipped += 1
                continue
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            downloaded += 1
        except Exception as exc:
            errors.append(f"{filename}: {exc}")

    if progress_cb:
        progress_cb(total, total, f"CDN icon sync complete: {downloaded} downloaded")

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "errors": errors,
        "heroes_written": len(roster),
    }
