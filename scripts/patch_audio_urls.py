"""
Patch sermons.jsonl: re-scrape audio_url (and add image_url) for entries
that still have the old /wp-content/uploads/ URLs.

Usage:
    python scripts/patch_audio_urls.py
    python scripts/patch_audio_urls.py --all   # re-scrape every entry
"""

import argparse
import json
import random
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

JSONL_PATH = Path(__file__).parent.parent / "utilities" / "sermons.jsonl"

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.thestandingchurch.com/",
})


def is_wrong_audio_url(audio_url: str) -> bool:
    """Return True if the audio_url uses the old /wp-content/uploads/ path."""
    decoded = unquote(audio_url)
    return "wp-content/uploads" in decoded


def fetch_audio_and_image(page_url: str):
    """Fetch a sermon page and return (audio_url, image_url) or (None, None) on failure."""
    try:
        r = session.get(page_url, timeout=15)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — skipping")
            return None, None
    except requests.RequestException as e:
        print(f"  Request error: {e}")
        return None, None

    soup = BeautifulSoup(r.text, "html.parser")

    audio_el = soup.select_one("a.wpfc-sermon-single-audio-download")
    audio_url = audio_el["href"] if audio_el and audio_el.get("href") else ""

    image_el = soup.select_one("img.wpfc-sermon-single-image-img")
    image_url = image_el["src"] if image_el and image_el.get("src") else ""

    return audio_url, image_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Re-scrape every entry, not just wrong ones")
    args = parser.parse_args()

    rows = []
    with open(JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))

    to_fix = [i for i, r in enumerate(rows) if args.all or is_wrong_audio_url(r.get("audio_url", ""))]
    print(f"Entries to patch: {len(to_fix)} / {len(rows)}")

    fixed = skipped = 0
    for n, i in enumerate(to_fix, 1):
        r = rows[i]
        print(f"[{n}/{len(to_fix)}] {r['title']}")
        audio_url, image_url = fetch_audio_and_image(r["url"])

        if audio_url:
            rows[i]["audio_url"] = audio_url
            rows[i]["image_url"] = image_url
            fixed += 1
            print(f"  audio: {audio_url}")
        else:
            print(f"  no audio found — keeping original")
            skipped += 1

        if n < len(to_fix):
            time.sleep(random.uniform(2.5, 5.0))

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nDone — fixed: {fixed}, skipped: {skipped}")


if __name__ == "__main__":
    main()
