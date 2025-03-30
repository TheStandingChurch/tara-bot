import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.thestandingchurch.com/sermons/"
PAGE_URL = "https://www.thestandingchurch.com/sermons/page/{}/"

def scrape_sermons():
    sermons = []
    
    # Loop through pages 1 to 12
    for page in range(11, 13):
        url = PAGE_URL.format(page)
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all sermon links
        sermon_links = [a["href"] for a in soup.select(".wpfc-sermon-title a")]

        for sermon_url in sermon_links:
            sermon_data = scrape_sermon_details(sermon_url)
            if sermon_data:
                sermons.append(sermon_data)

    return sermons

def scrape_sermon_details(sermon_url):
    """Scrapes details from an individual sermon page."""
    response = requests.get(sermon_url)
    if response.status_code != 200:
        print(f"Failed to fetch {sermon_url}")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract title
    title = soup.select_one(".wpfc-sermon-single-title").text.strip() if soup.select_one(".wpfc-sermon-single-title") else "No Title"

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
        "title": title,
        "cover_image": cover_url,
        "audio_url": audio_url,
        "description": description_text,
        "link": sermon_url
    }

if __name__ == "__main__":
    sermons = scrape_sermons()
    for sermon in sermons:  # Print first 5 results for testing
        print(sermon, "\n")
