import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import sys

visited = set()
lock = threading.Lock()

def is_valid_link(link, base_netloc):
    return link.startswith("http") and urlparse(link).netloc == base_netloc

def extract_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, tag["href"].split("#")[0])
        if full_url not in visited:
            links.add(full_url)
    return links

def search_keywords_in_page(url, keywords, base_netloc):
    try:
        with lock:
            if url in visited:
                return
            visited.add(url)
        print(f"[🔎] Scanning: {url}", flush=True)
        response = requests.get(url, timeout=5)
        html = response.text
        text = BeautifulSoup(html, "html.parser").get_text()
        matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]

        for match in matches:
            print(f"✅ Found '{match}' at: {url}", flush=True)

        # Recurse into child links
        child_links = extract_links(url, html)
        with ThreadPoolExecutor(max_workers=5) as executor:
            for link in child_links:
                if is_valid_link(link, base_netloc):
                    executor.submit(search_keywords_in_page, link, keywords, base_netloc)

    except Exception as e:
        print(f"Error scanning {url}: {str(e)}", flush=True)

def main(base_url, keywords):
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    base_netloc = urlparse(base_url).netloc.replace("www.", "")
    
    print(f"\n[🔍] Starting deep crawl of {base_url}", flush=True)
    print(f"[🔑] Keywords: {', '.join(keywords)}\n", flush=True)

    # Start crawling with threading
    search_keywords_in_page(base_url, keywords, base_netloc)
    print("\n[✅] Scan completed!", flush=True)

if __name__ == "__main__":
    base_url = input("Enter the base URL (e.g., https://srmrmp.edu.in): ").strip()
    keywords_input = input("Enter keywords separated by commas: ").strip()
    keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
    main(base_url, keywords)