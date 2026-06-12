from __future__ import annotations

"""
Scrape hero ability data from Template:Abilities/{WikiPage} on the Fandom wiki.

Data is stored as JSON files in hero_data/ at the project root, keyed by
hero slug (e.g. hero_data/Black_Cat.json, hero_data/Bruce_Banner.json).
"""

import json
import os
import re
import sys
import time

import requests

import datetime

WIKI_API = "https://marvelrivals.fandom.com/api.php"

if getattr(sys, 'frozen', False):
    _DATA_DIR = os.path.join(sys._MEIPASS, 'hero_data')
else:
    _DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "hero_data")
    )

_ICONS_DIR = os.path.join(_DATA_DIR, "ability_icons")

_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "ProfTracker/4.0 (educational project)"

_REQUEST_DELAY = float(os.environ.get("PROFTRACKER_REQUEST_DELAY", "0.5"))


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_template(path: str) -> str | None:
    """Fetch Template:{path} wikitext. path may contain spaces or &."""
    title = f"Template:{path.replace(' ', '_')}"
    resp = _SESSION.get(WIKI_API, params={
        "action": "parse", "page": title,
        "prop": "wikitext", "format": "json",
    }, timeout=20)
    resp.raise_for_status()
    d = resp.json()
    if "parse" not in d:
        return None
    return d["parse"]["wikitext"]["*"]


def fetch_abilities_wikitext(wiki_page: str) -> str | None:
    """Fetch top-level Template:Abilities/{wiki_page} wikitext."""
    return _fetch_template(f"Abilities/{wiki_page}")


def _extract_subtemplates(wikitext: str) -> list[tuple[str, str]]:
    """
    If wikitext contains SkillTable refs inside tabbers, return
    (form_label, template_path) pairs. Returns [] for simple templates.
    """
    refs = re.findall(r'\{\{SkillTable\|(?:1=)?([^}|]+)\}\}', wikitext)
    if not refs:
        return []

    results = []
    for ref in refs:
        path = ref.strip()
        parts = [p.strip() for p in path.split('/')]
        # parts[0]="Abilities", parts[1]=hero, parts[2]=form, parts[3]=sub (optional)
        form = parts[2] if len(parts) >= 3 else ""
        results.append((form, path))
    return results


def fetch_hero_abilities(wiki_page: str) -> list[dict]:
    """
    Fetch and parse all abilities for a hero.
    Handles single-template and multi-form (tabber) heroes.
    Returns flat list of ability dicts, each with optional 'form' key.
    """
    wt = fetch_abilities_wikitext(wiki_page)
    if wt is None:
        return []

    subtemplates = _extract_subtemplates(wt)
    if not subtemplates:
        return parse_abilities(wt)

    # Multi-form: fetch each sub-template and tag abilities with their form
    all_abilities: list[dict] = []
    seen_forms: set[str] = set()

    for form_label, path in subtemplates:
        sub_wt = _fetch_template(path)
        if sub_wt is None:
            continue
        form_abilities = parse_abilities(sub_wt)
        for a in form_abilities:
            # Only set form when there are multiple forms
            a["form"] = form_label
        all_abilities.extend(form_abilities)
        if form_label not in seen_forms:
            seen_forms.add(form_label)
        time.sleep(_REQUEST_DELAY)

    return all_abilities


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def _extract_blocks(wikitext: str) -> list[tuple[str, str]]:
    """Return list of (section_title, raw_block) for each Skill template."""
    results = []
    current_section = "General"
    i = 0
    n = len(wikitext)

    while i < n:
        # Section title
        m = re.match(r'\{\{Skill/Title\|([^}]+)\}\}', wikitext[i:])
        if m:
            current_section = m.group(1).strip()
            i += m.end()
            continue

        # Skill block (not Skill/Title or Skill/Header)
        if wikitext[i:i+7] == '{{Skill' and not re.match(
            r'\{\{Skill/(Title|Header)', wikitext[i:]
        ):
            depth = 0
            j = i
            while j < n:
                if wikitext[j:j+2] == '{{':
                    depth += 1
                    j += 2
                elif wikitext[j:j+2] == '}}':
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            results.append((current_section, wikitext[i:j]))
            i = j
            continue

        i += 1

    return results


def _clean_text(raw: str) -> str:
    """Remove wiki markup, ATC templates, and HTML tags."""
    # {{ATC|color|text}} → text
    text = re.sub(r'\{\{ATC\|[^|]+\|([^}]+)\}\}', r'\1', raw)
    # [[Link|Display]] → Display
    text = re.sub(r'\[\[[^\]]*\|([^\]]+)\]\]', r'\1', text)
    # [[Link]] → Link
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    # <br> tags → space
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
    # Any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Bold markers '''...'''
    text = re.sub(r"'''([^']+)'''", r'\1', text)
    return text.strip()


def _parse_key(raw: str) -> str:
    """Extract PC key from {{#switch:...| PC = Q |...}} or return raw."""
    m = re.search(r'PC\s*=\s*([^|}\s]+)', raw)
    if m:
        k = m.group(1).strip()
        _key_labels = {
            'lmb': 'Left Click', 'rmb': 'Right Click',
            'shift': 'Shift', 'space': 'Space',
            'Passive': 'Passive',
        }
        return _key_labels.get(k, k.upper())
    raw_clean = _clean_text(raw)
    return raw_clean if raw_clean else ''


def _parse_block(section: str, block: str) -> dict:
    """Parse one {{Skill...}} block into a structured dict."""
    fields: dict[str, str] = {}
    current_key = None
    current_val: list[str] = []

    for line in block.split('\n')[1:]:  # skip opening {{Skill... line
        stripped = line.strip()
        if stripped in ('}}', ''):
            continue
        if stripped.startswith('|') and '=' in stripped:
            if current_key:
                fields[current_key] = '\n'.join(current_val).strip()
            rest = stripped[1:]
            eq = rest.index('=')
            current_key = rest[:eq].strip()
            current_val = [rest[eq + 1:].strip()]
        elif current_key:
            current_val.append(line)

    if current_key:
        fields[current_key] = '\n'.join(current_val).strip()

    # Name — strip HTML styling and any embedded File: image references
    name_raw = fields.get('name', '')
    name_raw = re.sub(r'<[^>]+>', '', name_raw).strip()
    # Some abilities (e.g. Team-Up) embed the icon as [[File:name.ext|...]] or bare File:name.ext
    _file_re = re.compile(
        r'\[\[File:(.+?\.(?:png|jpg|jpeg|webp|gif))[^\]]*\]\]'   # [[File:name.ext|params]]
        r'|File:(.+?\.(?:png|jpg|jpeg|webp|gif))',                # bare File:name.ext
        re.IGNORECASE,
    )
    embedded_icon_m = _file_re.search(name_raw)
    embedded_icon = None
    if embedded_icon_m:
        embedded_icon = embedded_icon_m.group(1) or embedded_icon_m.group(2)
        name_raw = _file_re.sub('', name_raw)
    name = _clean_text(name_raw).strip()

    # Key binding
    key = _parse_key(fields.get('key', ''))

    # Description + stats
    desc_raw = fields.get('description', fields.get('description ', ''))
    parts = [p.strip() for p in desc_raw.split('----') if p.strip()]
    description = _clean_text(parts[0]) if parts else ''

    stats: dict[str, str] = {}
    for part in parts[1:]:
        m = re.match(r"'''([^']+?)\s*-\s*'''\s*(.*)", part, re.DOTALL)
        if m:
            stat_name = m.group(1).strip()
            stat_val = _clean_text(m.group(2))
            stats[stat_name] = stat_val

    # Icon: prefer explicit |icon field, fall back to filename embedded in name
    icon_raw = re.sub(r'^File:', '', fields.get('icon', '').strip(), flags=re.IGNORECASE)
    icon_m = re.match(r'^(.+?\.(?:png|jpg|jpeg|webp|gif))', icon_raw, re.IGNORECASE)
    icon = icon_m.group(1).strip() if icon_m else (embedded_icon or '')

    return {
        "section": section,
        "name": name,
        "key": key,
        "icon": icon,
        "description": description,
        "stats": stats,
    }


def parse_abilities(wikitext: str) -> list[dict]:
    """Parse full abilities template wikitext into a list of ability dicts."""
    blocks = _extract_blocks(wikitext)
    abilities = []
    for section, block in blocks:
        parsed = _parse_block(section, block)
        if parsed["name"]:
            abilities.append(parsed)
    return abilities


# ---------------------------------------------------------------------------
# Team-up group scraper
# ---------------------------------------------------------------------------

_TEAMUPS_PATH = os.path.join(_DATA_DIR, "team_ups.json")


# Wiki Team-Ups page uses hero display names; map to internal names where they differ.
_TEAMUP_HERO_ALIASES: dict[str, str] = {
    "Hulk": "Bruce Banner",
}


def _parse_teamup_block(block: str) -> dict | None:
    """Parse a single {{Teamup|...}} block into {name, anchor, partners}."""
    fields: dict[str, str] = {}
    for line in block.split('\n'):
        stripped = line.strip()
        if stripped.startswith('|') and '=' in stripped:
            rest = stripped[1:]
            eq = rest.index('=')
            fields[rest[:eq].strip()] = rest[eq + 1:].strip()

    name = fields.get('name', '').strip()
    if not name:
        return None

    heroes: list[str] = []
    for i in range(1, 10):
        logo = fields.get(f'i{i}', '').strip()
        if not logo:
            break
        # "Doctor Strange Hero Logo.png" → "Doctor Strange"
        # "Elsa Bloodstone Logo.png"     → "Elsa Bloodstone"
        hero_name = re.sub(
            r'\s+(?:Hero\s+)?Logo\.(?:png|jpg|webp)$', '', logo, flags=re.IGNORECASE
        ).strip()
        hero_name = _TEAMUP_HERO_ALIASES.get(hero_name, hero_name)
        if hero_name:
            heroes.append(hero_name)

    if len(heroes) < 2:
        return None

    return {"name": name, "anchor": heroes[0], "partners": heroes[1:]}


def _parse_teamups_page(wikitext: str) -> list[dict]:
    """Extract all {{Teamup}} blocks from the Team-Ups page wikitext."""
    results: list[dict] = []
    marker = '{{Teamup'
    start = 0
    while True:
        idx = wikitext.find(marker, start)
        if idx == -1:
            break
        after = wikitext[idx + len(marker):]
        if after and after[0] not in ('\n', '|', ' ', '}'):
            start = idx + 1
            continue
        depth = 0
        j = idx
        while j < len(wikitext):
            if wikitext[j:j + 2] == '{{':
                depth += 1
                j += 2
            elif wikitext[j:j + 2] == '}}':
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        parsed = _parse_teamup_block(wikitext[idx:j])
        if parsed:
            results.append(parsed)
        start = j
    return results


def scrape_teamups(progress_cb=None) -> dict:
    """
    Fetch team-up group data from the wiki Team-Ups page.
    Saves hero_data/team_ups.json with [{name, anchor, partners}].
    Returns {"count": int, "errors": list[str]}.
    """
    if progress_cb:
        progress_cb(0, 1, "Fetching Team-Ups page...")
    try:
        resp = _SESSION.get(WIKI_API, params={
            "action": "parse", "page": "Team-Ups",
            "prop": "wikitext", "format": "json",
        }, timeout=30)
        resp.raise_for_status()
        wikitext = resp.json()["parse"]["wikitext"]["*"]
    except Exception as exc:
        return {"count": 0, "errors": [f"Team-Ups page: {exc}"]}

    teamups = _parse_teamups_page(wikitext)
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_TEAMUPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(teamups, f, indent=2, ensure_ascii=False)

    if progress_cb:
        progress_cb(1, 1, f"Saved {len(teamups)} team-up groups")

    return {"count": len(teamups), "errors": []}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _ability_path(slug: str) -> str:
    return os.path.join(_DATA_DIR, f"{slug}.json")


def save_abilities(slug: str, abilities: list[dict]) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ability_path(slug), 'w', encoding='utf-8') as f:
        json.dump(abilities, f, indent=2, ensure_ascii=False)


def load_abilities(hero_name: str) -> list[dict]:
    slug = hero_name.replace(' ', '_').replace('&', '%26')
    path = _ability_path(slug)
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Ability icon downloads
# ---------------------------------------------------------------------------

def ability_icon_path(icon_filename: str) -> str:
    return os.path.join(_ICONS_DIR, icon_filename.replace(" ", "_"))


def _to_local_icon_name(ability_name: str, wiki_filename: str) -> str:
    """Return a clean local filename derived from the ability name."""
    ext = os.path.splitext(wiki_filename)[1].lower() or ".png"
    slug = re.sub(r"[^\w\s-]", "", ability_name).strip()
    slug = re.sub(r"\s+", "_", slug)
    return f"{slug}{ext}"


def _resolve_and_download_icons(icon_pairs: list[tuple[str, str]]) -> list[str]:
    """
    Download missing ability icons.
    icon_pairs: list of (wiki_filename, local_filename).
    Looks up CDN URL by wiki_filename, saves to local_filename.
    Returns error list.
    """
    os.makedirs(_ICONS_DIR, exist_ok=True)
    missing = [(wiki, local) for wiki, local in icon_pairs
               if wiki and local and not os.path.exists(ability_icon_path(local))]
    if not missing:
        return []

    errors = []
    chunk_size = 30
    cdn_map: dict[str, str] = {}

    wiki_names = [wiki for wiki, _ in missing]
    for i in range(0, len(wiki_names), chunk_size):
        chunk = wiki_names[i:i + chunk_size]
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
                cdn_map[title] = ii[0]["url"]
        if i + chunk_size < len(wiki_names):
            time.sleep(_REQUEST_DELAY)

    for wiki_name, local_name in missing:
        url = cdn_map.get(wiki_name)
        if not url:
            errors.append(f"No CDN URL: {wiki_name}")
            continue
        try:
            r = _SESSION.get(url, timeout=30, stream=True)
            r.raise_for_status()
            with open(ability_icon_path(local_name), "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            time.sleep(0.05)
        except Exception as exc:
            errors.append(f"{wiki_name}: {exc}")

    return errors


# ---------------------------------------------------------------------------
# Sync entry point
# ---------------------------------------------------------------------------

def sync_abilities(icon_sets: list[dict], progress_cb=None) -> dict:
    """
    Fetch and store abilities for all primary heroes.
    progress_cb(current, total, message) called per hero.
    Returns {"fetched": int, "skipped": int, "errors": list[str]}.
    """
    primary = [s for s in icon_sets if s.get("is_primary") and s.get("wiki_page")]
    fetched = 0
    skipped = 0
    errors: list[str] = []
    all_icon_pairs: list[tuple[str, str]] = []
    seen_pairs: set[str] = set()

    for i, s in enumerate(primary):
        slug = s["slug"]
        wiki_page = s["wiki_page"]
        path = _ability_path(slug)

        if progress_cb:
            progress_cb(i, len(primary), f"Abilities: {wiki_page}")

        if os.path.exists(path):
            skipped += 1
            continue

        try:
            abilities = fetch_hero_abilities(wiki_page)
            if not abilities:
                errors.append(f"No abilities template: {wiki_page}")
                continue
            # Rename icon field from wiki filename to ability-name-based local filename
            for a in abilities:
                wiki_name = a.get("icon", "")
                if wiki_name:
                    local_name = _to_local_icon_name(a["name"], wiki_name)
                    a["icon"] = local_name
                    key = f"{wiki_name}|{local_name}"
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        all_icon_pairs.append((wiki_name, local_name))
            save_abilities(slug, abilities)
            fetched += 1
            time.sleep(_REQUEST_DELAY)
        except Exception as exc:
            errors.append(f"{wiki_page}: {exc}")

    if progress_cb:
        progress_cb(len(primary), len(primary), "Downloading ability icons...")

    icon_errors = _resolve_and_download_icons(all_icon_pairs)
    errors.extend(icon_errors)

    if progress_cb:
        progress_cb(len(primary), len(primary), "Abilities sync complete")

    return {"fetched": fetched, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Release date scraping
# ---------------------------------------------------------------------------

_RELEASE_DATE_PATTERNS = [
    r'\|\s*game_release\s*=\s*([^\n|{}]+)',
    r'\|\s*release_date\s*=\s*([^\n|{}]+)',
    r'\|\s*release\s*=\s*([^\n|{}]+)',
    r'\|\s*released\s*=\s*([^\n|{}]+)',
]

_DATE_FMTS = ["%B %d, %Y", "%B %Y", "%Y-%m-%d"]


def _parse_release_date_str(wikitext: str) -> str | None:
    for pattern in _RELEASE_DATE_PATTERNS:
        m = re.search(pattern, wikitext, re.IGNORECASE)
        if m:
            raw = _clean_text(m.group(1).strip())
            if raw:
                return raw
    return None


def is_future_release(date_str: str) -> bool:
    """Return True if date_str represents a future or unannounced release."""
    if not date_str:
        return False
    upper = date_str.upper()
    if any(kw in upper for kw in ("TBA", "UPCOMING", "COMING SOON", "TO BE ANNOUNCED", "SEASON")):
        return True
    today = datetime.date.today()
    for fmt in _DATE_FMTS:
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt).date() > today
        except ValueError:
            continue
    # Fall back to year-only check
    m = re.search(r'\b(20\d{2})\b', date_str)
    if m:
        return int(m.group(1)) > today.year
    return False


def fetch_release_dates(icon_sets: list[dict], progress_cb=None) -> dict[str, str]:
    """
    Fetch release dates for all primary heroes from their wiki pages.
    Always re-fetches (not cached) so upcoming heroes update when released.
    Returns {hero_name: date_string} — only heroes with a parseable date included.
    """
    primary = [s for s in icon_sets if s.get("is_primary") and s.get("wiki_page")]
    dates: dict[str, str] = {}

    for i, s in enumerate(primary):
        wiki_page = s["wiki_page"]
        hero_name = s["slug"].replace("_", " ").replace("%26", "&")
        if progress_cb:
            progress_cb(i, len(primary), f"Release date: {wiki_page}")
        try:
            resp = _SESSION.get(WIKI_API, params={
                "action": "query", "titles": wiki_page,
                "prop": "revisions", "rvprop": "content", "format": "json",
            }, timeout=20)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                revs = page.get("revisions", [])
                if revs:
                    wt = revs[0].get("*") or revs[0].get("slots", {}).get("main", {}).get("*", "")
                    date_str = _parse_release_date_str(wt)
                    if date_str:
                        dates[hero_name] = date_str
                    elif re.search(r'\{\{(UpcomingContent|NextCharacter)\}\}', wt, re.IGNORECASE):
                        season_m = re.search(r'Season\s+(\d+\.\d+)', wt) or re.search(r'Season\s+(\d+)', wt)
                        dates[hero_name] = f"Season {season_m.group(1)}" if season_m else "TBA"
            time.sleep(_REQUEST_DELAY)
        except Exception:
            pass  # best-effort; don't fail the sync

    return dates


# ---------------------------------------------------------------------------
# Official site scraper (marvelrivals.com) — replaces wiki ability scraper
# ---------------------------------------------------------------------------

_OFFICIAL_HEROES_URL = "https://www.marvelrivals.com/heroes/index.html"
_OFFICIAL_UA = {"User-Agent": "Mozilla/5.0"}

# Internal hero names that differ from the official site's display names.
_OFFICIAL_NAME_ALIASES: dict[str, str] = {
    "bruce banner": "HULK",
}

_OFFICIAL_TYPE_SECTION: dict[int, str] = {
    1: "Normal Attack",
    2: "Abilities",
    3: "Team-Up Abilities",
}


def _fetch_official_index() -> dict[str, str]:
    """
    Fetch marvelrivals.com/heroes and return {UPPERCASE_NAME: page_url}
    for every hero listed.
    """
    import html as _html_mod
    resp = _SESSION.get(_OFFICIAL_HEROES_URL, headers=_OFFICIAL_UA, timeout=30)
    resp.raise_for_status()
    page = resp.text
    pairs: list[tuple[str, str]] = re.findall(
        r'title="([^"]+)"[^>]*data-url="([^"]+)"', page
    )
    if not pairs:
        rev = re.findall(r'data-url="([^"]+)"[^>]*title="([^"]+)"', page)
        pairs = [(b, a) for a, b in rev]
    return {_html_mod.unescape(name).upper().strip(): url for name, url in pairs}


def _parse_official_hero_page(html: str) -> list[dict]:
    """
    Parse ability rows from an official hero page (the dated HTML behind data-url).
    Returns ability dicts; each has a temporary '_icon_url' key to strip before saving.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    inner = soup.find(class_="art-inner-content")
    if not inner:
        return []
    table = inner.find("table", class_="table-imgs")
    if not table:
        return []

    abilities: list[dict] = []
    for row in table.find_all("tr"):
        cols = row.find_all("td", recursive=False)
        if len(cols) < 5:
            continue
        try:
            row_type = int(cols[0].get_text(strip=True))
        except ValueError:
            continue
        if row_type == 0:
            continue

        section = _OFFICIAL_TYPE_SECTION.get(row_type, "Abilities")
        name = cols[1].get_text(strip=True)
        if not name:
            continue

        icon_url = ""
        img = cols[2].find("img")
        if img:
            icon_url = img.get("src", "")

        description = cols[3].get_text(strip=True)

        stats: dict[str, str] = {}
        stats_table = cols[4].find("table")
        if stats_table:
            for stat_row in stats_table.find_all("tr"):
                stat_cols = stat_row.find_all("td")
                if len(stat_cols) >= 2:
                    k = stat_cols[0].get_text(strip=True)
                    v = stat_cols[1].get_text(strip=True)
                    if k:
                        stats[k] = v

        key = stats.pop("Key", "")
        local_icon = ""
        if icon_url:
            icon_slug = re.sub(r"[^\w\s-]", "", name).strip()
            icon_slug = re.sub(r"\s+", "_", icon_slug)
            local_icon = f"{icon_slug}.png"

        abilities.append({
            "section": section,
            "name": name,
            "key": key,
            "icon": local_icon,
            "_icon_url": icon_url,
            "description": description,
            "stats": stats,
        })
    return abilities


def sync_abilities_official(icon_sets: list[dict], progress_cb=None) -> dict:
    """
    Fetch and store abilities for all primary heroes from the official marvelrivals.com.
    Drop-in replacement for sync_abilities().
    Returns {"fetched": int, "skipped": int, "errors": list[str]}.
    """
    if progress_cb:
        progress_cb(0, 1, "Fetching hero index from marvelrivals.com...")
    try:
        index = _fetch_official_index()
    except Exception as exc:
        return {"fetched": 0, "skipped": 0, "errors": [f"Official hero index: {exc}"]}

    primary = [s for s in icon_sets if s.get("is_primary") and s.get("wiki_page")]
    fetched = skipped = 0
    errors: list[str] = []
    os.makedirs(_DATA_DIR, exist_ok=True)
    os.makedirs(_ICONS_DIR, exist_ok=True)

    for i, s in enumerate(primary):
        slug = s["slug"]
        hero_name = s["wiki_page"]
        path = _ability_path(slug)

        if progress_cb:
            progress_cb(i, len(primary), f"Abilities: {hero_name}")

        if os.path.exists(path):
            skipped += 1
            continue

        official_name = _OFFICIAL_NAME_ALIASES.get(hero_name.lower(), hero_name.upper())
        page_url = index.get(official_name)
        if not page_url:
            errors.append(f"Not in official index: {hero_name}")
            skipped += 1
            continue

        try:
            resp = _SESSION.get(page_url, headers=_OFFICIAL_UA, timeout=20)
            resp.raise_for_status()
            abilities = _parse_official_hero_page(resp.text)
            if not abilities:
                errors.append(f"No abilities parsed: {hero_name}")
                continue

            for ability in abilities:
                icon_url = ability.pop("_icon_url", "")
                local_name = ability.get("icon", "")
                if icon_url and local_name:
                    dest = ability_icon_path(local_name)
                    if not os.path.exists(dest):
                        try:
                            ir = _SESSION.get(icon_url, headers=_OFFICIAL_UA,
                                              timeout=20, stream=True)
                            ir.raise_for_status()
                            with open(dest, "wb") as f:
                                for chunk in ir.iter_content(8192):
                                    f.write(chunk)
                        except Exception as exc:
                            errors.append(f"icon {local_name}: {exc}")

            save_abilities(slug, abilities)
            fetched += 1
            time.sleep(_REQUEST_DELAY)
        except Exception as exc:
            errors.append(f"{hero_name}: {exc}")

    if progress_cb:
        progress_cb(len(primary), len(primary), "Abilities sync complete")
    return {"fetched": fetched, "skipped": skipped, "errors": errors}


def sync_abilities_from_cdn(slugs: list[str], progress_cb=None) -> dict:
    """
    Download per-hero ability JSON files, team_ups.json, and ability icons
    from PROFTRACKER_CDN_BASE instead of scraping the wiki.

    Returns {"fetched": int, "skipped": int, "errors": list[str]}.
    """
    cdn_base = os.environ.get("PROFTRACKER_CDN_BASE", "").rstrip("/")
    if not cdn_base:
        raise RuntimeError("PROFTRACKER_CDN_BASE is not set")

    os.makedirs(_DATA_DIR, exist_ok=True)
    os.makedirs(_ICONS_DIR, exist_ok=True)
    fetched = skipped = 0
    errors: list[str] = []

    total = len(slugs) + 1  # +1 for team_ups.json

    # Download team_ups.json
    if progress_cb:
        progress_cb(0, total, "Downloading team_ups.json from CDN...")
    try:
        r = _SESSION.get(f"{cdn_base}/hero_data/team_ups.json", timeout=15)
        r.raise_for_status()
        with open(_TEAMUPS_PATH, "w", encoding="utf-8") as f:
            f.write(r.text)
    except Exception as exc:
        errors.append(f"team_ups.json: {exc}")

    # Download per-hero ability JSONs + their ability icons
    for i, slug in enumerate(slugs):
        if progress_cb:
            progress_cb(i + 1, total, f"Abilities: {slug.replace('_', ' ')}...")
        path = _ability_path(slug)
        if os.path.exists(path):
            skipped += 1
            continue
        try:
            r = _SESSION.get(f"{cdn_base}/hero_data/{slug}.json", timeout=15)
            if r.status_code == 404:
                skipped += 1
                continue
            r.raise_for_status()
            abilities: list[dict] = r.json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(abilities, f, indent=2, ensure_ascii=False)
            fetched += 1

            for ability in abilities:
                icon_name = ability.get("icon", "")
                if not icon_name:
                    continue
                icon_dest = ability_icon_path(icon_name)
                if os.path.exists(icon_dest):
                    continue
                try:
                    ir = _SESSION.get(
                        f"{cdn_base}/hero_data/ability_icons/{icon_name}",
                        timeout=30, stream=True,
                    )
                    if ir.status_code == 404:
                        continue
                    ir.raise_for_status()
                    with open(icon_dest, "wb") as f:
                        for chunk in ir.iter_content(8192):
                            f.write(chunk)
                except Exception as exc:
                    errors.append(f"icon {icon_name}: {exc}")

        except Exception as exc:
            errors.append(f"{slug}: {exc}")

    if progress_cb:
        progress_cb(total, total, "Abilities CDN sync complete")

    return {"fetched": fetched, "skipped": skipped, "errors": errors}
