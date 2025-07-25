import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import sys
import time
import random
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global variables
visited = set()
lock = threading.Lock()
MAX_RETRIES = 3
MAX_DEPTH = 3
MAX_WORKERS = 3  # Reduced from 5
TIMEOUT = 15  # Increased from 10

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
]

# Free proxies - these might expire or stop working. In production, you would use a proxy service.
FREE_PROXIES = [
    None,  # First option is direct connection
    'http://34.73.161.164:3128',
    'http://165.227.139.1:80',
    'http://165.227.119.235:80',
    'http://34.195.196.27:3128',
]

def get_random_user_agent():
    """Get a random user agent from the defined list"""
    return {
        'User-Agent': USER_AGENTS[random.randint(0, len(USER_AGENTS)-1)]
    }

def get_random_proxy():
    return random.choice(FREE_PROXIES)

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

def request_with_retry(url, depth, try_proxies=False):
    """Make a request with retry logic and proxy support"""
    # Print status immediately for better real-time feedback
    if depth == 0:
        print(f"\n[🔍] Starting deep crawl (Max depth: {MAX_DEPTH})", flush=True)
    
    headers = get_random_user_agent()
    
    retries = 0
    last_error = None
    proxies_to_try = [None]  # Start with direct connection
    
    # If we should try proxies, add some to the list
    if try_proxies:
        # We'll try a direct connection and two random proxies
        proxies_to_try.extend([get_random_proxy(), get_random_proxy()])
    
    for proxy in proxies_to_try:
        current_proxy = None
        if proxy:
            current_proxy = {'http': proxy, 'https': proxy}
            print(f"[🔀] Trying with proxy: {proxy}", flush=True)
        else:
            print(f"[🔄] Trying direct connection", flush=True)
            
        retries = 0
        while retries < MAX_RETRIES:
            try:
                # Add a delay that increases with depth to reduce server load
                delay = random.uniform(0.3, 1.0) * (depth + 1)  # Further reduced delay
                time.sleep(delay)
                
                # Print status more frequently for better feedback
                if retries > 0:
                    print(f"[⏱️] Attempt {retries+1}/{MAX_RETRIES} for {url}", flush=True)
                
                # Make the request with custom headers and without SSL verification
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=TIMEOUT,
                    verify=False,  # Bypass SSL certificate verification
                    proxies=current_proxy  # Use proxy if provided
                )
                
                # Check if we got a successful response
                if response.status_code != 200:
                    print(f"[⚠️] Got status code {response.status_code} for {url}", flush=True)
                    if retries < MAX_RETRIES - 1:
                        retries += 1
                        wait_time = 2 ** retries + random.uniform(0, 1)
                        print(f"[⏱️] Retry {retries}/{MAX_RETRIES} after {wait_time:.1f}s", flush=True)
                        time.sleep(wait_time)
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                last_error = e
                retries += 1
                if retries < MAX_RETRIES:
                    wait_time = 2 ** retries + random.uniform(0, 1)  # Exponential backoff
                    print(f"[⏱️] Retry {retries}/{MAX_RETRIES} after {wait_time:.1f}s ({str(e)[:50]}...)", flush=True)
                    time.sleep(wait_time)
                else:
                    print(f"[❌] Failed with {'proxy ' + proxy if proxy else 'direct connection'}: {url}", flush=True)
                    print(f"[❌] Error: {str(e)[:100]}...", flush=True)
                    break  # Go to next proxy
    
    # If we get here, all proxies failed
    if last_error:
        raise last_error
    else:
        raise Exception(f"Failed to fetch {url} after trying multiple proxies and retries")

def search_keywords_in_page(url, keywords, base_netloc, depth=0):
    try:
        with lock:
            if url in visited:
                return
            visited.add(url)
            
        # Check max depth
        if depth > MAX_DEPTH:
            print(f"[📏] Max depth reached at: {url}", flush=True)
            return
            
        print(f"[🔎] Scanning: {url}", flush=True)
        
        # Get the page with retries and random user agent
        try:
            response = request_with_retry(url, depth, try_proxies=(depth==0))  # Only try proxies for the initial URL
            html = response.text
            text = BeautifulSoup(html, "html.parser").get_text()
            
            # Find keywords
            matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
            for match in matches:
                print(f"✅ Found '{match}' at: {url}", flush=True)

            # Only crawl further if we're not too deep
            if depth < MAX_DEPTH:
                # Extract links and limit the number we process
                child_links = extract_links(url, html)
                
                # Limit links to reduce load (maximum 15 links per page)
                if len(child_links) > 15:
                    child_links = random.sample(list(child_links), 15)
                    
                print(f"[🌐] Found {len(child_links)} links on {url}", flush=True)
                
                if len(child_links) == 0:
                    print(f"[⚠️] No links found on {url}", flush=True)
                
                # Create a list of valid links to process
                valid_links = []
                for link in child_links:
                    # Make sure we haven't visited this URL and it's on the same domain
                    if link not in visited and is_valid_link(link, base_netloc):
                        valid_links.append(link)
                
                # Process each link recursively with ThreadPoolExecutor
                if valid_links:
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = []
                        for link in valid_links:
                            futures.append(executor.submit(search_keywords_in_page, link, keywords, base_netloc, depth + 1))
                        
                        # Wait for all futures to complete
                        for future in futures:
                            try:
                                future.result()
                            except Exception as e:
                                print(f"[❌] Thread error: {str(e)}", flush=True)
        
        except Exception as e:
            print(f"[❌] Error processing {url}: {str(e)}", flush=True)
            # Even if this URL fails, we've already added it to visited, so continue crawling

    except Exception as e:
        print(f"[❌] Error scanning {url}: {str(e)}", flush=True)

def main(url, keywords, max_depth=2, use_proxies=False, connect_test_only=False):
    global visited, MAX_DEPTH
    MAX_DEPTH = max_depth
    visited = set()

    print(f"[🚀] Starting Deep Crawl of {url}")
    print(f"[📋] Keywords: {', '.join(keywords)}")
    
    if max_depth == 0:
        print(f"[📊] Mode: Fast Scan (No Depth - only scanning initial page)")
    elif max_depth == -1:
        print(f"[📊] Mode: TURBO (No limits, maximum crawling of all pages)")
        MAX_DEPTH = 999  # Effectively unlimited depth
    else:
        print(f"[📊] Max depth: {max_depth}")
    
    # Ensure URL has http/https protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get the base netloc for URL validation
    base_netloc = urlparse(url).netloc.replace('www.', '')
    
    if connect_test_only:
        print(f"[🔍] Testing connection to {url}...")
        try:
            response = requests.get(url, headers=get_random_user_agent(), 
                                  timeout=10, verify=False)
            print(f"[✅] Connection successful! Status code: {response.status_code}")
            return []
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"[❌] Connection failed: {error_msg}")
            return []

    # Only use proxies for normal mode with depth > 0
    if use_proxies and max_depth > 0:
        print("[🔀] Using proxy rotation for this scan")
    
    try:
        print(f"[🔍] Scanning: {url}")
        
        # Handle special TURBO mode
        if max_depth == -1:
            # Get initial page content
            response = request_with_retry(url, 0, try_proxies=False)
            initial_html = response.text
            # Start turbo crawl
            turbo_crawl(url, keywords, initial_html, base_netloc)
        else:
            # Normal crawl
            search_keywords_in_page(url, keywords, base_netloc, 0)
        
        print("[✅] Scan completed!")
        
    except Exception as e:
        print(f"[❌] Error during scan: {str(e)}")
        raise

def turbo_crawl(start_url, keywords, initial_html, base_netloc):
    """Special function for turbo mode that aggressively crawls all pages"""
    global visited
    visited = set()
    all_links_found = set()
    
    print(f"[⚡] TURBO MODE ACTIVATED! Scanning at maximum speed with NO LIMITS...")
    print(f"[⚡] WARNING: This mode ignores all security measures and rate limits")
    print(f"[⚡] WARNING: Only use on your own websites or with explicit permission")
    
    # Add initial URL to visited set
    visited.add(start_url)
    
    # Process initial page
    if initial_html:
        print(f"[🔍] Processing initial page: {start_url}")
        links = turbo_process_url_and_get_links(start_url, keywords, all_links_found, base_netloc)
        all_links_found.update(links)
    
    # Process all found links
    while all_links_found:
        current_batch = list(all_links_found)[:30]  # Process in batches of 30
        all_links_found = all_links_found - set(current_batch)
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = []
            for url in current_batch:
                if url not in visited:
                    futures.append(executor.submit(turbo_process_url_and_get_links, url, keywords, all_links_found, base_netloc))
            
            # Wait for all futures to complete
            for future in futures:
                try:
                    new_links = future.result()
                    all_links_found.update(new_links)
                except Exception as e:
                    print(f"[❌] Error processing URL in turbo mode: {str(e)}")
    
    print(f"[⚡] Turbo crawl finished! Scanned {len(visited)} URLs")

def turbo_process_url_and_get_links(url, keywords, all_links_found, main_domain):
    """Process a single URL in turbo mode and return new links found"""
    try:
        # Add to visited set
        with lock:
            if url in visited:
                return set()
            visited.add(url)
        
        print(f"[🔍] Processing: {url}")
        
        # Make request with minimal delay
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENTS[0]},
            timeout=5,
            verify=False
        )
        
        if response.status_code != 200:
            print(f"[⚠️] Got status {response.status_code} for {url}")
            return set()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Search for keywords
        text = soup.get_text()
        matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
        for match in matches:
            print(f"✅ Found '{match}' at: {url}")
        
        # Extract all links
        new_links = set()
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                full_url = urljoin(url, href.split("#")[0])
                if full_url.startswith('http'):
                    parsed_url = urlparse(full_url)
                    if parsed_url.netloc and main_domain in parsed_url.netloc:
                        if full_url not in visited and full_url not in all_links_found:
                            new_links.add(full_url)
        
        return new_links
        
    except Exception as e:
        print(f"[❌] Error processing {url}: {str(e)}")
        return set()

def scan_link(url, keywords, depth, use_proxies=False):
    if url in visited or depth <= 0:
        return
        
    print(f"[🔍] Scanning {url} (depth: {depth})")
    
    try:
        # Update to use the correct parameters
        response = request_with_retry(url, depth, try_proxies=use_proxies)
        if not response or response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get the base netloc from the URL
        base_netloc = urlparse(url).netloc.replace('www.', '')
        
        # Search for keywords using the correct function parameters
        search_keywords_in_page(url, keywords, base_netloc, depth)
                    
    except Exception as e:
        print(f"[❌] Error scanning {url}: {str(e)[:100]}...")

# Global variable to store results for statistics
scan_results = []

def append_to_results(line):
    scan_results.append(line)
    return line

if __name__ == "__main__":
    base_url = input("Enter the base URL (e.g., https://srmrmp.edu.in): ").strip()
    keywords_input = input("Enter keywords separated by commas: ").strip()
    keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
    depth_input = input("Enter maximum crawl depth (default 3): ").strip()
    max_depth = int(depth_input) if depth_input.isdigit() else 3
    main(base_url, keywords, max_depth)