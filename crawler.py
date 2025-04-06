import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# Base URL of the college site
BASE_URL = "https://www.srmrmp.edu.in"

# Keywords to search for
KEYWORDS = [
    "Harshitha", "Chowdary", "Kanderi",
    "harshichowdary25", "hk1724"
]

# Visited pages to avoid duplicates
visited = set()

# Limit to avoid crawling the entire internet
MAX_PAGES = 50

# Crawl starting from homepage
def crawl(url, depth=0):
    if len(visited) >= MAX_PAGES or url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url, timeout=10)
        if "text/html" not in response.headers["Content-Type"]:
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # Search for keywords in the page content
        text = soup.get_text()
        for keyword in KEYWORDS:
            if re.search(keyword, text, re.IGNORECASE):
                print(f"[FOUND] '{keyword}' on {url}")

        # Crawl internal links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/"):
                next_url = urljoin(BASE_URL, href)
            elif href.startswith("http") and BASE_URL in href:
                next_url = href
            else:
                continue

            crawl(next_url, depth + 1)

    except Exception as e:
        print(f"[ERROR] {url} - {e}")

# Start crawling
crawl(BASE_URL)
