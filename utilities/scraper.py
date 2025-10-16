import os
import requests
from bs4 import BeautifulSoup
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.thestandingchurch.com/sermons/"
PAGE_URL = "https://www.thestandingchurch.com/sermons/page/{}/"

# Create a requests session with retry logic and headers
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})

retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)


def scrape_sermons():
    sermons = []

    for page in range(4, 6):
        url = PAGE_URL.format(page)
        try:
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to fetch {url} (status {response.status_code})")
                continue
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all sermon links
        sermon_links = [a["href"] for a in soup.select(".wpfc-sermon-title a")]
        print(f"📄 Page {page}: Found {len(sermon_links)} sermons")

        for sermon_url in sermon_links:
            sermon_data = scrape_sermon_details(sermon_url)
            if sermon_data:
                sermons.append(sermon_data)
            time.sleep(1)  # polite delay

    return sermons


def scrape_sermon_details(sermon_url):
    """Scrapes details from an individual sermon page."""
    try:
        response = session.get(sermon_url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to fetch {sermon_url} (status {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching {sermon_url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title = soup.select_one(".wpfc-sermon-single-title")
    title_text = title.text.strip() if title else "No Title"

    # Extract cover image
    cover_img = soup.select_one("img.wpfc-sermon-single-image-img")
    cover_url = cover_img["src"] if cover_img else "No Image"

    # Extract audio link
    audio_player = soup.select_one(".wpfc-sermon-player source")
    audio_url = audio_player["src"] if audio_player else "No Audio"

    # Extract description
    description = soup.select_one(".wpfc-sermon-single-main > p")
    description_text = description.text.strip() if description else "No Description"

    return {
        "title": title_text,
        "cover_image": cover_url,
        "audio_url": audio_url,
        "description": description_text,
        "link": sermon_url
    }


if __name__ == "__main__":
    print("🚀 Starting sermon scraper...")
    sermons = scrape_sermons()

    save_path = os.path.join(os.path.dirname(__file__), "sermons.jsonl")
    print(f"💾 Saving to {save_path}")

    with open(save_path, "a", encoding="utf-8") as f:
        for sermon in sermons:
            if sermon:  # only write non-empty dicts
                f.write(json.dumps(sermon, ensure_ascii=False) + "\n")

    print(f"✅ Saved {len(sermons)} sermons to sermons.jsonl")