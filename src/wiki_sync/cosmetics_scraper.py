from __future__ import annotations

"""
Scrape hero costume (skin) data from rivalskins.com.

Data is stored as JSON in hero_data/{slug}_skins.json, with one entry per
costume. Recolor relationships (parent skin ID + name) are resolved via the
individual skin detail page, which explicitly labels recolors.
"""

import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

RIVALSKINS_BASE = "https://rivalskins.com"

if getattr(sys, 'frozen', False):
    _DATA_DIR = os.path.join(sys._MEIPASS, 'hero_data')
else:
    _DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "hero_data")
    )

_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "ProfTracker/2.0.0 (educational project)"

_REQUEST_DELAY = float(os.environ.get("PROFTRACKER_REQUEST_DELAY", "0.5"))

_QUALITY_LABELS = {
    "quality_1": "Common",
    "quality_2": "Rare",
    "quality_3": "Epic",
    "quality_4": "Legendary",
}

# Heroes where the internal name differs from the rivalskins.com slug.
_SLUG_ALIASES: dict[str, str] = {
    "Bruce Banner": "hulk",
}


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _hero_slug(hero_name: str) -> str:
    if hero_name in _SLUG_ALIASES:
        return _SLUG_ALIASES[hero_name]
    slug = hero_name.lower()
    slug = slug.replace("&", "and")
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def _quality_from_class(classes: list[str]) -> str:
    for cls in classes:
        if cls.startswith("quality-"):
            key = cls.replace("quality-", "quality_")
            return _QUALITY_LABELS.get(key, "Unknown")
    return "Unknown"


def _item_id_from_url(href: str) -> int | None:
    m = re.search(r"/item/(\d+)/", href)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_hero_costumes(hero_name: str) -> list[dict]:
    """
    Fetch costume list from rivalskins.com/hero/{slug}/.
    Returns list of partial skin dicts (missing detail-page fields).
    """
    slug = _hero_slug(hero_name)
    url = f"{RIVALSKINS_BASE}/hero/{slug}/"
    resp = _SESSION.get(url, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    costumes = []

    for a in soup.find_all("a", attrs={"data-type": "costume"}):
        item_id_str = a.get("data-id")
        href = a.get("href", "").strip()
        if not item_id_str or not href:
            continue

        item_id = int(item_id_str)

        # Rarity from wrapper div class e.g. "bundle-card-img-wrapper quality-4"
        wrapper = a.find("div", class_="bundle-card-img-wrapper")
        rarity = _quality_from_class(wrapper.get("class", [])) if wrapper else "Unknown"

        # Image URL — prefer .png src for compatibility
        img = a.find("img")
        image_url = img["src"] if img else ""

        # Name from .bundle-name div
        name_div = a.find("div", class_="bundle-name")
        name = name_div.get_text(strip=True) if name_div else ""

        detail_url = href if href.startswith("http") else RIVALSKINS_BASE + href

        costumes.append({
            "item_id": item_id,
            "_detail_url": detail_url,
            "name": name,
            "rarity": rarity,
            "image_url": image_url,
            "costume_url": None,
            "source": None,
            "season": None,
            "release_date": None,
            "recolor_of_id": None,
            "recolor_of_name": None,
        })

    return costumes


def fetch_skin_detail(costume: dict) -> None:
    """
    Fetch the detail page for a costume and populate source, season,
    release_date, recolor_of_id, and recolor_of_name in-place.
    """
    resp = _SESSION.get(costume["_detail_url"], timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "?source=" in href:
            costume["source"] = text
        elif "?season=" in href:
            costume["season"] = text
        elif "/item/" in href and "RECOLOR OF" in text.upper():
            costume["recolor_of_id"] = _item_id_from_url(href)
            m = re.match(r"RECOLOR OF (.+?) COSTUME", text, re.IGNORECASE)
            if m:
                costume["recolor_of_name"] = m.group(1).title()

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text.startswith("Release Date:"):
            costume["release_date"] = text.removeprefix("Release Date:").strip()
            break

    # Full-body costume image (separate from the headshot icon)
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        if "/img_" in src and "/img_icon_" not in src and src.endswith(".png"):
            costume["costume_url"] = src
            break
    # Fallback: derive from icon URL by stripping the _icon_ segment
    if not costume.get("costume_url") and "/img_icon_" in (costume.get("image_url") or ""):
        costume["costume_url"] = costume["image_url"].replace("/img_icon_", "/img_")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

_SKIN_ICONS_DIR    = os.path.join(_DATA_DIR, "skin_icons")
_SKIN_COSTUMES_DIR = os.path.join(_DATA_DIR, "skin_costumes")


def skin_icon_path(item_id: int) -> str:
    return os.path.join(_SKIN_ICONS_DIR, f"{item_id}.png")


def skin_costume_path(item_id: int) -> str:
    return os.path.join(_SKIN_COSTUMES_DIR, f"{item_id}.png")


def _download_skin_images(costumes: list[dict]) -> list[str]:
    """Download headshot icon and full-body costume images for each skin."""
    os.makedirs(_SKIN_ICONS_DIR, exist_ok=True)
    os.makedirs(_SKIN_COSTUMES_DIR, exist_ok=True)
    errors = []
    for costume in costumes:
        item_id = costume.get("item_id")
        if not item_id:
            continue

        for url, dest_fn in (
            (costume.get("image_url"),   skin_icon_path(item_id)),
            (costume.get("costume_url"), skin_costume_path(item_id)),
        ):
            if not url or os.path.exists(dest_fn):
                continue
            try:
                r = _SESSION.get(url, timeout=20, stream=True)
                r.raise_for_status()
                with open(dest_fn, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                time.sleep(0.05)
            except Exception as exc:
                errors.append(f"skin image {item_id}: {exc}")
    return errors


def _skin_path(slug: str) -> str:
    return os.path.join(_DATA_DIR, f"{slug}_skins.json")


def save_skins(slug: str, skins: list[dict]) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_skin_path(slug), "w", encoding="utf-8") as f:
        json.dump(skins, f, indent=2, ensure_ascii=False)


def load_skins(hero_name: str) -> list[dict]:
    slug = hero_name.replace(" ", "_").replace("&", "%26")
    path = _skin_path(slug)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CDN sync (downloads from S3 instead of scraping rivalskins.com)
# ---------------------------------------------------------------------------

def sync_skins_from_cdn(slugs: list[str], progress_cb=None) -> dict:
    """
    Download skin JSON files + images from PROFTRACKER_CDN_BASE.
    Mirrors scrape_skins() signature; returns the same result dict.
    """
    cdn_base = os.environ.get("PROFTRACKER_CDN_BASE", "").rstrip("/")
    if not cdn_base:
        raise RuntimeError("PROFTRACKER_CDN_BASE is not set")

    os.makedirs(_DATA_DIR, exist_ok=True)
    os.makedirs(_SKIN_ICONS_DIR, exist_ok=True)
    os.makedirs(_SKIN_COSTUMES_DIR, exist_ok=True)

    fetched = skipped = 0
    errors: list[str] = []

    for i, slug in enumerate(slugs):
        if progress_cb:
            progress_cb(i, len(slugs), f"Skins: {slug.replace('_', ' ')}")

        path = _skin_path(slug)
        if os.path.exists(path):
            skipped += 1
            continue

        try:
            r = _SESSION.get(f"{cdn_base}/hero_data/{slug}_skins.json", timeout=15)
            if r.status_code == 404:
                skipped += 1
                continue
            r.raise_for_status()
            skins: list[dict] = r.json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(skins, f, indent=2, ensure_ascii=False)
            fetched += 1

            # Download skin icon and costume image for each skin
            for skin in skins:
                item_id = skin.get("item_id")
                if not item_id:
                    continue
                for dest_fn, prefix in (
                    (skin_icon_path(item_id),    "skin_icons"),
                    (skin_costume_path(item_id), "skin_costumes"),
                ):
                    if os.path.exists(dest_fn):
                        continue
                    try:
                        ir = _SESSION.get(
                            f"{cdn_base}/hero_data/{prefix}/{item_id}.png",
                            timeout=30, stream=True,
                        )
                        if ir.status_code == 404:
                            continue
                        ir.raise_for_status()
                        with open(dest_fn, "wb") as f:
                            for chunk in ir.iter_content(8192):
                                f.write(chunk)
                    except Exception as exc:
                        errors.append(f"skin image {item_id}: {exc}")

        except Exception as exc:
            errors.append(f"{slug}: {exc}")

    if progress_cb:
        progress_cb(len(slugs), len(slugs), "Skins CDN sync complete")

    return {"fetched": fetched, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Sync entry point (scrapes rivalskins.com directly)
# ---------------------------------------------------------------------------

def scrape_skins(icon_sets: list[dict], progress_cb=None) -> dict:
    """
    Scrape costume data for all primary heroes from rivalskins.com.
    Saves hero_data/{slug}_skins.json per hero.
    Returns {"fetched": int, "skipped": int, "errors": list[str]}.
    """
    primary = [s for s in icon_sets if s.get("is_primary") and s.get("slug")]
    fetched = skipped = 0
    errors: list[str] = []

    for i, s in enumerate(primary):
        slug = s["slug"]
        hero_name = slug.replace("_", " ").replace("%26", "&")
        path = _skin_path(slug)

        if progress_cb:
            progress_cb(i, len(primary), f"Skins: {hero_name}")

        if os.path.exists(path):
            skipped += 1
            continue

        try:
            costumes = fetch_hero_costumes(hero_name)
            if not costumes:
                errors.append(f"No costumes found: {hero_name}")
                skipped += 1
                continue

            time.sleep(_REQUEST_DELAY)

            for j, costume in enumerate(costumes):
                fetch_skin_detail(costume)
                del costume["_detail_url"]
                if j < len(costumes) - 1:
                    time.sleep(_REQUEST_DELAY)

            save_skins(slug, costumes)
            img_errors = _download_skin_images(costumes)
            errors.extend(img_errors)
            fetched += 1

        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                errors.append(f"Hero page not found on rivalskins.com: {hero_name}")
            else:
                errors.append(f"{hero_name}: {exc}")
        except Exception as exc:
            errors.append(f"{hero_name}: {exc}")

    if progress_cb:
        progress_cb(len(primary), len(primary), "Skins sync complete")

    return {"fetched": fetched, "skipped": skipped, "errors": errors}
