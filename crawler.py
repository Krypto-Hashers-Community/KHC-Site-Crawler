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
                
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = []
                    for link in child_links:
                        if is_valid_link(link, base_netloc):
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
            print(f"[⚡] TURBO MODE ACTIVATED! Scanning at maximum speed with NO LIMITS...", flush=True)
            print(f"[⚡] WARNING: This mode ignores all security measures and rate limits", flush=True)
            print(f"[⚡] WARNING: Only use on your own websites or with explicit permission", flush=True)
            
            # Direct request without retries or proxies for maximum speed
            try:
                response = requests.get(
                    url, 
                    headers={'User-Agent': USER_AGENTS[0]},
                    timeout=3,  # Even shorter timeout
                    verify=False  # Skip SSL verification
                )
                html = response.text
                
                # Continue with turbo mode - call a special function
                turbo_crawl(url, keywords, html, base_netloc)
                print(f"[✅] Turbo scan completed! Scanned {len(visited)} URLs")
            except Exception as e:
                print(f"[❌] Initial connection failed in Turbo mode: {str(e)}", flush=True)
                print(f"[⚡] Attempting to continue anyway...", flush=True)
                # Create a minimal set to start with
                turbo_crawl(url, keywords, "", base_netloc)
            
            return []
        
        # Fast Scan mode (depth = 0)
        elif max_depth == 0:
            print(f"[🔍] Fast Scan Mode: Direct request to {url}", flush=True)
            # Direct request without retries or proxies for faster speed
            response = requests.get(
                url, 
                headers=get_random_user_agent(),  # Still use random agent for basic protection
                timeout=10,
                verify=False  # Skip SSL verification
            )
            
            if response.status_code != 200:
                print(f"[❌] Failed to access {url}. Status code: {response.status_code}")
                return []
                
            html = response.text
            
            # Get the text from the HTML
            text = BeautifulSoup(html, "html.parser").get_text()
            
            # Find keywords directly
            print(f"[🔎] Fast scanning initial page only: {url}", flush=True)
            matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
            for match in matches:
                print(f"✅ Found '{match}' at: {url}", flush=True)
            
            print(f"[✅] Fast scan completed! Scanned 1 URL")
            return []
            
        # Standard mode - Use the first implementation of request_with_retry
        else:
            response = request_with_retry(url, 0, try_proxies=use_proxies)
            if not response or response.status_code != 200:
                print(f"[❌] Failed to access {url}. Status code: {response.status_code if response else 'N/A'}")
                return []
                
            # Parse the HTML content
            html = response.text
            
            # Use the original search_keywords_in_page function that takes url, keywords, base_netloc as args
            search_keywords_in_page(url, keywords, base_netloc, depth=0)
        
    except Exception as e:
        print(f"[❌] Error crawling {url}: {str(e)}")
    
    print(f"[✅] Scan completed! Scanned {len(visited)} URLs")
    return []

def turbo_crawl(start_url, keywords, initial_html, base_netloc):
    """Ultra-fast crawling without any delays or protection features"""
    print(f"[⚡] Starting turbo crawl from {start_url}", flush=True)
    print(f"[⚡] UNLIMITED mode: Will scan ALL pages on the site", flush=True)
    
    # Add the URL to visited (global set)
    global visited
    visited.add(start_url)
    
    # Queue of URLs to process - using a set for the queue to track pending URLs
    queue = set([start_url])
    processed = 0
    all_links_found = set()  # Track all links we've seen to avoid re-queueing
    all_links_found.add(start_url)
    
    # Extract the domain for matching
    parsed_start_url = urlparse(start_url)
    domain = parsed_start_url.netloc
    print(f"[⚡] Domain for scanning: {domain}", flush=True)
    
    # Try multiple methods to extract domain parts for flexible matching
    domain_parts = domain.split('.')
    if len(domain_parts) >= 2:
        main_domain = '.'.join(domain_parts[-2:])  # e.g., example.com
    else:
        main_domain = domain
    
    print(f"[⚡] Will match URLs with domain: {main_domain}", flush=True)
    
    # Process the initial page
    try:
        if initial_html:
            soup = BeautifulSoup(initial_html, "html.parser")
            text = soup.get_text()
            
            # Find keywords
            matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
            for match in matches:
                print(f"✅ Found '{match}' at: {start_url}", flush=True)
            
            # Extract links from initial page - get ALL links
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    full_url = urljoin(start_url, href.split("#")[0])
                    # Basic URL validity check
                    if full_url not in all_links_found and full_url.startswith('http'):
                        parsed_url = urlparse(full_url)
                        # Use simple domain matching - much more reliable
                        if parsed_url.netloc and main_domain in parsed_url.netloc:
                            queue.add(full_url)
                            all_links_found.add(full_url)
                            print(f"[⚡] Added to queue: {full_url}", flush=True)
    except Exception as e:
        # Just log and continue
        print(f"[⚡] Error processing initial page: {str(e)}", flush=True)
        print(f"[⚡] Will try to continue with direct website access", flush=True)
        
        # If initial HTML processing failed, try a direct request
        try:
            response = requests.get(
                start_url, 
                headers={'User-Agent': USER_AGENTS[0]},
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract links from the page
                for tag in soup.find_all("a", href=True):
                    href = tag["href"].strip()
                    if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                        full_url = urljoin(start_url, href.split("#")[0])
                        if full_url not in all_links_found and full_url.startswith('http'):
                            parsed_url = urlparse(full_url)
                            if parsed_url.netloc and main_domain in parsed_url.netloc:
                                queue.add(full_url)
                                all_links_found.add(full_url)
                                print(f"[⚡] Added to queue: {full_url}", flush=True)
        except Exception as e:
            print(f"[⚡] Direct request also failed: {str(e)}", flush=True)
    
    print(f"[⚡] Initial queue size: {len(queue)}", flush=True)
    
    # Process queue with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=30) as executor:  # Increased to 30 workers
        futures = []
        
        # Process each URL in the queue - ABSOLUTELY NO LIMITS
        while queue:
            # Get a batch of URLs to process
            batch = list(queue)[:50]  # Process up to 50 URLs at once
            queue = queue.difference(batch)  # Remove them from the queue
            
            print(f"[⚡] Processing batch of {len(batch)} URLs", flush=True)
            
            # Submit all URLs in the batch to be processed in parallel
            batch_futures = []
            for url in batch:
                future = executor.submit(turbo_process_url_and_get_links, url, keywords, all_links_found, main_domain)
                batch_futures.append(future)
                futures.append(future)
            
            # Wait for batch to complete
            for future in batch_futures:
                try:
                    # Get new links from this batch
                    new_links = future.result(timeout=15)
                    
                    # Add any new links to the queue
                    for link in new_links:
                        if link not in all_links_found:
                            queue.add(link)
                            all_links_found.add(link)
                            visited.add(link)  # Add to global visited set
                except Exception as e:
                    # Log exception but continue
                    print(f"[⚡] Error in future: {str(e)}", flush=True)
            
            processed += len(batch)
            
            # Status update
            print(f"[⚡] Turbo processed {processed} pages, {len(queue)} remaining in queue", flush=True)
        
    print(f"[⚡] Turbo crawl finished! Processed {processed} pages", flush=True)

def turbo_process_url_and_get_links(url, keywords, all_links_found, main_domain):
    """Process a URL in turbo mode and return any new links found"""
    new_links = set()
    try:
        # Advanced headers to bypass common restrictions
        headers = {
            'User-Agent': USER_AGENTS[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        
        # Super fast request with minimal options
        response = requests.get(
            url, 
            timeout=3,  # Reduced timeout to 3 seconds
            verify=False,
            headers=headers,
            allow_redirects=True  # Follow redirects
        )
        
        # Print status updates less frequently to maximize speed
        if random.random() < 0.1:  # Only 10% of requests show status
            print(f"[⚡] Processing: {url}", flush=True)
        
        # Get any status code that returns content
        content = response.text if response.status_code < 400 else ""
            
        # Process even partial responses if we got any content
        if content:
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text()
            
            # Find keywords
            matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
            for match in matches:
                print(f"✅ Found '{match}' at: {url}", flush=True)
            
            # Extract ALL links from the page
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    full_url = urljoin(url, href.split("#")[0])
                    # Only check for basic URL validity and not being in all_links_found
                    if full_url not in all_links_found and full_url.startswith('http'):
                        parsed_url = urlparse(full_url)
                        # Make sure it's on the same domain or subdomain - simpler check
                        if parsed_url.netloc and main_domain in parsed_url.netloc:
                            new_links.add(full_url)
                
    except requests.RequestException:
        # Silent fail for requests errors
        pass
    except Exception as e:
        # Log the error but continue
        if random.random() < 0.1:  # Only log 10% of errors to reduce output spam
            print(f"[⚡] Error processing {url}: {str(e)[:50]}...", flush=True)
        
    return new_links

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