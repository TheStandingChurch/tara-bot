import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import openai
import psycopg
import requests
from bs4 import BeautifulSoup
from pgvector.psycopg import register_vector

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

    for page in range(1, 3):
        url = PAGE_URL.format(page)
        try:
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch {url} (status {response.status_code})")
                continue
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        sermon_links = [a["href"] for a in soup.select(".wpfc-sermon-title a")]
        print(f"Page {page}: Found {len(sermon_links)} sermons")

        for sermon_url in sermon_links:
            sermon_data = scrape_sermon_details(sermon_url)
            if sermon_data:
                sermons.append(sermon_data)
            time.sleep(1)  # polite delay

    return sermons


def scrape_sermon_details(sermon_url):
    try:
        response = session.get(sermon_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {sermon_url} (status {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {sermon_url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one(".wpfc-sermon-single-title")
    title_text = title.text.strip() if title else "No Title"

    cover_img = soup.select_one("img.wpfc-sermon-single-image-img")
    cover_url = cover_img["src"] if cover_img else "No Image"

    audio_player = soup.select_one(".wpfc-sermon-player source")
    audio_url = audio_player["src"] if audio_player else "No Audio"

    description = soup.select_one(".wpfc-sermon-single-main > p")
    description_text = description.text.strip() if description else "No Description"

    return {
        "title": title_text,
        "cover_image": cover_url,
        "audio_url": audio_url,
        "description": description_text,
        "link": sermon_url,
    }


def save_to_db(sermons: list[dict], database_url: str, api_key: str) -> None:
    """Embed scraped sermons and insert them into Postgres."""
    client = openai.OpenAI(api_key=api_key)

    with psycopg.connect(database_url) as conn:
        register_vector(conn)

        for sermon in sermons:
            if not sermon:
                continue

            text = sermon.get("description") or sermon.get("title", "")
            media = sermon.get("cover_image")
            audios = [sermon["audio_url"]] if sermon.get("audio_url") else []

            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small",
            )
            embedding = response.data[0].embedding

            conn.execute(
                """
                INSERT INTO messages (category, text, media, audios, embedding)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT messages_category_text_uq DO NOTHING
                """,
                ("life", text, media, audios, embedding),
            )
            conn.commit()
            print(f"Saved: {text[:60]}...")


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL", "")
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY", "")

    print("Starting sermon scraper...")
    sermons = scrape_sermons()
    print(f"Scraped {len(sermons)} sermons")

    if database_url and api_key:
        save_to_db(sermons, database_url, api_key)
    else:
        print("DATABASE_URL or OPENAI_API_KEY not set — skipping DB save.")
