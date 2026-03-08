import os
import re
import base64
import random
import requests
from bs4 import BeautifulSoup
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.thestandingchurch.com/sermons/"
PAGE_URL = "https://www.thestandingchurch.com/sermons/page/{}/"

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

retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)


def fetch(url):
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            return r
        print(f"  ❌ {url} → HTTP {r.status_code}")
    except requests.RequestException as e:
        print(f"  ⚠️ {url} → {e}")
    return None


def get_total_pages():
    r = fetch(BASE_URL)
    if not r:
        return 1
    soup = BeautifulSoup(r.text, "html.parser")
    nums = []
    for a in soup.select("a.page-numbers"):
        try:
            nums.append(int(a.get_text(strip=True).replace(",", "")))
        except ValueError:
            pass
    return max(nums) if nums else 1


def get_sermon_links(page):
    url = BASE_URL if page == 1 else PAGE_URL.format(page)
    r = fetch(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    return [a["href"] for a in soup.select("h3.wpfc-sermon-title a") if a.get("href")]


def decode_audio(encoded):
    """Decode base64-encoded mp3 URL used by MP3jPlayer."""
    try:
        # Fix padding
        encoded += "=" * (-len(encoded) % 4)
        return base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return None


def scrape_sermon(url):
    r = fetch(url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    html = r.text

    # Title
    title_el = soup.select_one(".wpfc-sermon-single-title")
    title = title_el.get_text(strip=True) if title_el else ""

    # Description: paragraphs inside the sermon main content area
    content = soup.select_one(".wpfc-sermon-single-main")
    if content:
        paras = [p.get_text(strip=True) for p in content.find_all("p") if p.get_text(strip=True)]
        description = "\n\n".join(paras)
    else:
        description = ""

    # Audio: MP3jPlayer encodes the URL as base64 in a JS variable
    audio_url = ""
    match = re.search(r'mp3\s*:\s*["\']([A-Za-z0-9+/=]{20,})["\']', html)
    if match:
        decoded = decode_audio(match.group(1))
        if decoded and decoded.startswith("http"):
            audio_url = decoded

    # Preacher
    preacher_el = soup.select_one("a[href*='preacher']")
    preacher = preacher_el.get_text(strip=True) if preacher_el else ""

    # Date
    date_el = soup.select_one("time[datetime]")
    if date_el:
        date = date_el.get("datetime", date_el.get_text(strip=True))
    else:
        date_el = soup.select_one(".entry-date, .posted-on")
        date = date_el.get_text(strip=True) if date_el else ""

    return {
        "title": title,
        "description": description,
        "audio_url": audio_url,
        "preacher": preacher,
        "date": date,
        "url": url,
    }


def scrape_all(start_page=1):
    total = get_total_pages()
    print(f"📚 Found {total} pages to scrape (starting from page {start_page})")

    sermons = []
    for page in range(start_page, total + 1):
        links = get_sermon_links(page)
        print(f"📄 Page {page}/{total}: {len(links)} sermons")

        # Longer pause between listing pages; extra cooldown every 10 pages
        if page > 1:
            if page % 10 == 0:
                cooldown = random.uniform(20.0, 35.0)
                print(f"  💤 Cooldown {cooldown:.0f}s after page {page}...")
                time.sleep(cooldown)
            else:
                time.sleep(random.uniform(4.0, 8.0))

        for url in links:
            data = scrape_sermon(url)
            if data:
                sermons.append(data)
                print(f"  ✅ {data['title']}")
            time.sleep(random.uniform(2.5, 5.0))  # polite delay

    return sermons


if __name__ == "__main__":
    import sys
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    mode = "a" if start > 1 else "w"  # append when resuming

    print("🚀 Starting sermon scraper...")
    sermons = scrape_all(start_page=start)

    save_path = os.path.join(os.path.dirname(__file__), "sermons.jsonl")
    print(f"\n💾 Saving to {save_path} (mode={mode})")

    with open(save_path, mode, encoding="utf-8") as f:
        for s in sermons:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"✅ Done — {len(sermons)} sermons saved")
