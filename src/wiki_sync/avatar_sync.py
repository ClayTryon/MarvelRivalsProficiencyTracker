"""
Parse the Marvel Rivals Fandom Avatars page and download Hero / Lord / Champion icons.

Icon filename convention (local Icons/ folder):
  Hero_Icon_{slug}.png
  Lord_Icon_{slug}.png
  Champion_Icon_{slug}_Animated.gif

where slug = hero_name.replace(" ", "_").replace("&", "%26"), derived from the
Lord icon filename (most consistent naming in the wikitext).
"""

import os
import re
import sys
import time

import requests

WIKI_API = "https://marvelrivals.fandom.com/api.php"

if getattr(sys, 'frozen', False):
    ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
else:
    ICONS_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Icons")
    )

_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "ProfTracker/4.0 (educational project)"


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


_HEROES_PY = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "heroes.py")
)


def write_heroes_py(icon_sets: list[dict]) -> int:
    """
    Regenerate src/data/heroes.py from primary icon sets.
    Returns the number of heroes written.
    """
    primary = sorted(
        [s for s in icon_sets if s["is_primary"]],
        key=lambda s: _slug_to_name(s["slug"]),
    )

    names  = [_slug_to_name(s["slug"]) for s in primary]
    roles  = {_slug_to_name(s["slug"]): s["role"] for s in primary}

    lines = ["HERO_ROSTER = ["]
    for name in names:
        lines.append(f'    "{name}",')
    lines.append("]\n")
    lines.append("HERO_ROLES: dict[str, str] = {")
    for name in names:
        lines.append(f'    "{name}": "{roles[name]}",')
    lines.append("}\n")

    with open(_HEROES_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

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
            time.sleep(0.3)

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
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                downloaded += 1
                time.sleep(0.05)
            except Exception as exc:
                errors.append(f"{local_name}: {exc}")

        if progress_cb:
            hero_display = s["slug"].replace("_", " ").replace("%26", "&")
            progress_cb(i + 1, len(icon_sets), hero_display)

    return {"downloaded": downloaded, "skipped": skipped, "errors": errors}
