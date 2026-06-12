"""
Headless wiki sync for EC2. Scrapes the Fandom wiki and uploads output to S3.

Usage (on the EC2 instance):
    S3_BUCKET=proftracker-wiki-data python -m wiki_sync.server_sync

Requires boto3 and the EC2 instance profile to have s3:PutObject / s3:ListBucket
on the target bucket. No PyQt6, EasyOCR, or GPU needed.
"""

import logging
import os
import sys

# Allow running as `python -m wiki_sync.server_sync` from the project root,
# or as `python src/wiki_sync/server_sync.py` directly.
_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from wiki_sync.avatar_sync import (
    ICONS_DIR,
    heroes_json_path,
    parse_avatars_page,
    sync_icons,
    update_release_dates,
    write_heroes_py,
)
from wiki_sync.ability_scraper import (
    _DATA_DIR,
    _ICONS_DIR as _ABILITY_ICONS_DIR,
    fetch_release_dates,
    scrape_teamups,
    sync_abilities,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

_BUCKET = os.environ.get("S3_BUCKET", "")


def _upload(s3, local_path: str, s3_key: str) -> None:
    s3.upload_file(local_path, _BUCKET, s3_key)
    log.info("  uploaded → s3://%s/%s", _BUCKET, s3_key)


def _progress(current: int, total: int, msg: str) -> None:
    tag = f"{current}/{total}" if total > 0 else "..."
    log.info("[%s] %s", tag, msg)


def run_server_sync() -> None:
    if not _BUCKET:
        raise RuntimeError("S3_BUCKET environment variable is not set")

    import boto3
    s3 = boto3.client("s3")

    # ── Phase 1: avatars + icons ──────────────────────────────────────────────
    log.info("=== Phase 1: fetching avatar roster from wiki ===")
    icon_sets = parse_avatars_page()
    log.info("Parsed %d icon sets", len(icon_sets))
    sync_icons(icon_sets, progress_cb=_progress)
    hero_count = write_heroes_py(icon_sets)
    log.info("heroes.json written — %d heroes", hero_count)

    # ── Phase 2: abilities + team-ups ─────────────────────────────────────────
    log.info("=== Phase 2: scraping hero abilities ===")
    sync_abilities(icon_sets, progress_cb=_progress)

    log.info("=== Phase 3: scraping team-ups ===")
    scrape_teamups(progress_cb=_progress)

    log.info("=== Phase 3b: fetching hero release dates ===")
    release_dates = fetch_release_dates(icon_sets, progress_cb=_progress)
    update_release_dates(release_dates)
    log.info("Release dates updated for %d heroes", len(release_dates))

    # ── Phase 4: upload to S3 ─────────────────────────────────────────────────
    log.info("=== Phase 4: uploading to S3 ===")

    # heroes.json
    _upload(s3, heroes_json_path(), "heroes.json")

    # Icons/ → icons/ prefix
    uploaded_icons = 0
    for filename in sorted(os.listdir(ICONS_DIR)):
        if filename.lower().endswith((".png", ".gif", ".webp")):
            _upload(s3, os.path.join(ICONS_DIR, filename), f"icons/{filename}")
            uploaded_icons += 1
    log.info("Uploaded %d hero icons", uploaded_icons)

    # hero_data/*.json → hero_data/ prefix
    uploaded_data = 0
    for filename in sorted(os.listdir(_DATA_DIR)):
        if filename.endswith(".json"):
            _upload(s3, os.path.join(_DATA_DIR, filename), f"hero_data/{filename}")
            uploaded_data += 1
    log.info("Uploaded %d ability/teamup JSON files", uploaded_data)

    # hero_data/ability_icons/ → hero_data/ability_icons/ prefix
    uploaded_ability_icons = 0
    if os.path.isdir(_ABILITY_ICONS_DIR):
        for filename in sorted(os.listdir(_ABILITY_ICONS_DIR)):
            _upload(
                s3,
                os.path.join(_ABILITY_ICONS_DIR, filename),
                f"hero_data/ability_icons/{filename}",
            )
            uploaded_ability_icons += 1
    log.info("Uploaded %d ability icons", uploaded_ability_icons)

    log.info(
        "=== Done: %d heroes, %d hero icons, %d data files, %d ability icons ===",
        hero_count, uploaded_icons, uploaded_data, uploaded_ability_icons,
    )


if __name__ == "__main__":
    run_server_sync()
