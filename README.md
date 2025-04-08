# 🕷️ KHC Site Crawler

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-brightgreen)
![Flask](https://img.shields.io/badge/flask-2.0%2B-red)
![Status](https://img.shields.io/badge/status-active-success.svg)

> A blazingly fast, concurrent web crawler built for developers who need to search for keywords across websites that don't offer native search functionality. Built with Python, Flask, and modern web technologies.

## 📋 Table of Contents

- [🔥 Features](#-features)
- [⚡ Installation](#-installation)
- [🚀 Usage](#-usage)
- [🧰 Advanced Configuration](#-advanced-configuration)
- [🔌 API Reference](#-api-reference)
- [🛠️ Technical Architecture](#️-technical-architecture)
- [🧩 How It Works](#-how-it-works)
- [⚠️ Limitations](#️-limitations)
- [🔮 Future Enhancements](#-future-enhancements)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)

---

## 🔥 Features

### Core Functionality
- **Deep Web Crawling**: Recursively crawls web pages up to a specified depth (supports depths 1-5)
- **Concurrent Processing**: Multi-threaded architecture for efficient scanning using Python's ThreadPoolExecutor
- **Keyword Detection**: Fast regex-based pattern matching for finding keywords in page content
- **Respect for Website Structure**: Only follows links within the same domain

### Advanced Crawler Features
- **URL Normalization**: Handles different formats of the same URL to avoid duplicate crawling
- **Depth Control**: Configurable depth limit to prevent excessive crawling
- **Request Management**:
  - Exponential backoff retry mechanism for failed requests
  - Random delay between requests to reduce server load 
  - Timeout handling for stalled requests
  - Custom user agent rotation to avoid detection

### User Experience Enhancements
- **Real-Time Progress Display**: Live terminal-like output showing crawling progress
- **Interactive Results**: Double-click on found keywords to open the corresponding URL
- **Results Counter**: Live-updating badge showing the count of found URL matches
- **Status Indicators**: Visual status indicators (Processing/Error/Complete)
- **Export Functionality**: Download scan results for offline analysis

### Security & Performance
- **SSL Verification Override**: Option to bypass SSL certificate verification for testing environments
- **Proxy Support**: Configurable proxy rotation to avoid IP-based blocking
- **Connection Testing**: Test connections before starting a full scan
- **Output Capture**: Non-blocking output handling for smooth UI updates

---

## ⚡ Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- Modern web browser

### Quick Install

```bash
# Clone this repository
git clone https://github.com/yourusername/KHC-Site-Crawler.git

# Navigate to the project directory
cd KHC-Site-Crawler

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Docker Installation

```bash
# Build the Docker image
docker build -t khc-site-crawler .

# Run the container
docker run -p 5000:5000 khc-site-crawler
```

---

## 🚀 Usage

### Starting a Scan

1. **Access the Web Interface**:
   - Open your browser and navigate to `http://localhost:5000`
   - You'll be greeted with the KHC Site Crawler welcome screen

2. **Enter URL**:
   - Input the target website URL (e.g., `example.com` or `https://example.com`)
   - The protocol (http/https) will be added automatically if omitted
   - Click "Next" to proceed

3. **Configure Scan Parameters**:
   - **Keywords**: Enter one or more keywords separated by commas
   - **Crawl Depth**: Select the depth of crawling
     - Shallow (2): Quick but limited coverage
     - Normal (3): Balanced performance and coverage
     - Deep (4): Extended coverage, slower performance
     - Very Deep (5): Exhaustive scanning, significantly slower
   - **Proxy Usage**: Toggle to enable/disable proxy rotation for bypassing restrictions
   - Click "Start Scanning" to begin

4. **Monitor Progress**:
   - The terminal output window shows real-time scanning progress with color coding:
     - 🔍 Blue: Information messages
     - ⚠️ Yellow: Warning messages
     - ❌ Red: Error messages
     - ✅ Green: Success messages
   - The status button indicates current scan state:
     - Processing (yellow): Scan in progress
     - Error (red): Scan encountered critical errors
     - Complete (green): Scan successfully completed

5. **View Results**:
   - Found keywords appear in the results section as they're discovered
   - The counter badge shows the total number of unique URLs with matches
   - Double-click on any result to open the corresponding page in a new tab
   - Use "Open All Found URLs" to open all matching pages at once

6. **Export Results**:
   - Click "Download Results" to save a text file with all scan output and found keywords

### Keyboard Shortcuts

- `Enter` in URL field: Proceed to keywords page if URL is valid
- `Enter` in keywords field: Start scanning if keywords are provided

---

## 🧰 Advanced Configuration

### Proxy Configuration

The application supports custom proxy configurations for advanced users. Modify the `FREE_PROXIES` list in `crawler.py`:

```python
FREE_PROXIES = [
    None,  # Direct connection
    'http://your-proxy-server:port',
    'http://another-proxy:port',
]
```

### User Agent Rotation

Add or modify user agents in the `USER_AGENTS` list in `crawler.py`:

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    # Add your custom user agent strings here
]
```

### Timeout and Workers Configuration

Adjust the crawler's timeout and concurrency settings by modifying the global variables in `crawler.py`:

```python
MAX_RETRIES = 3  # Maximum number of retry attempts
MAX_DEPTH = 3    # Default maximum crawl depth
MAX_WORKERS = 3  # Number of concurrent threads
TIMEOUT = 15     # Request timeout in seconds
```

---

## 🔌 API Reference

### Backend Routes

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/` | GET | Renders the main application page | None |
| `/start_scan` | POST | Initiates a new scan | `url`, `keywords`, `max_depth`, `use_proxies` |
| `/get_scan_results` | GET | Retrieves current scan results | None |
| `/download_results` | GET | Downloads scan results as text file | None |

### Example API Usage

```javascript
// Start a scan
fetch('/start_scan', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        url: 'example.com',
        keywords: ['keyword1', 'keyword2'],
        max_depth: 3,
        use_proxies: true
    })
})
.then(response => response.json())
.then(data => console.log(data));

// Get scan results
fetch('/get_scan_results')
.then(response => response.json())
.then(data => {
    console.log('Scan Results:', data.scan_results);
    console.log('Found Keywords:', data.found_keywords);
    console.log('Is Scanning:', data.is_scanning);
});
```

---

## 🛠️ Technical Architecture

### Component Overview

KHC Site Crawler follows a modern web application architecture with three main components:

1. **Flask Backend**:
   - Serves the web interface
   - Manages the crawling process in a separate thread
   - Provides API endpoints for frontend communication
   - Captures and stores crawler output

2. **Crawler Engine**:
   - Performs recursive website traversal
   - Handles HTTP requests with retry logic
   - Implements concurrent processing for efficiency
   - Detects keywords using regex pattern matching

3. **Web Frontend**:
   - Provides an intuitive user interface
   - Displays real-time crawling progress
   - Updates results dynamically with AJAX polling
   - Offers interactive results with direct URL access

### Data Flow

```
+------------------+       +-----------------+       +------------------+
|                  |       |                 |       |                  |
|  User Interface  |------>|  Flask Server   |------>|  Crawler Engine  |
|  (HTML/CSS/JS)   |       |  (Python/Flask) |       |  (Python)        |
|                  |<------|                 |<------|                  |
+------------------+       +-----------------+       +------------------+
                               |         ^
                               |         |
                               v         |
                           +----------------------+
                           |                      |
                           |  Output Capture &    |
                           |  Results Storage     |
                           |                      |
                           +----------------------+
```

---

## 🧩 How It Works

### Crawling Process

1. **Initialization**:
   - The application captures the base URL, keywords, max depth, and proxy settings
   - A separate thread is spawned to run the crawler
   - Output capture is initialized to redirect crawler output

2. **URL Processing**:
   - The crawler starts with the base URL
   - For each URL, the crawler:
     - Adds the URL to the visited set
     - Sends an HTTP request with retry logic
     - Parses the HTML content with BeautifulSoup
     - Searches for keywords in the text content
     - Extracts links for further crawling

3. **Concurrent Execution**:
   - A ThreadPoolExecutor manages crawling multiple URLs simultaneously
   - Each URL is processed in a separate thread
   - Thread-safe operations use a mutex lock to prevent race conditions

4. **Output Handling**:
   - Terminal output is captured in real-time
   - Lines containing keyword matches are identified and stored
   - Output is sent to the frontend via polling

### Example Request Flow

For a typical scan:

```
1. User submits scan configuration
2. Frontend sends POST request to /start_scan
3. Backend spawns crawler thread
4. Frontend begins polling /get_scan_results
5. Crawler processes URLs and finds keywords
6. Output is captured and sent to frontend
7. Frontend updates UI with results
8. Scan completes and status is updated
9. User can interact with or export results
```

---

## ⚠️ Limitations

- **Respect for robots.txt**: The crawler does not currently respect robots.txt directives
- **JavaScript Rendering**: The crawler doesn't execute JavaScript, so content loaded dynamically may not be crawled
- **Form Authentication**: Cannot crawl pages behind login forms or authentication walls
- **Rate Limiting**: While the crawler implements delays, aggressive crawling may trigger rate limiting
- **Resource Intensive**: Deep crawling of large sites may consume significant system resources
- **Single-Domain Focus**: The crawler remains within a single domain and doesn't follow external links

---

## 🔮 Future Enhancements

- [ ] **Advanced Filtering**: Content filtering by type, date, or relevance
- [ ] **Robots.txt Support**: Respecting website crawling policies
- [ ] **Headless Browser Integration**: Using Selenium/Puppeteer for JavaScript rendering
- [ ] **Authentication Support**: Crawling behind login forms
- [ ] **Schedule Scans**: Set up recurring scans with notifications
- [ ] **Differential Results**: Compare scan results over time
- [ ] **Export Formats**: Add support for CSV, JSON, and PDF exports
- [ ] **Custom Regex Patterns**: Allow more complex search patterns
- [ ] **Sitemap Support**: Use XML sitemaps for more efficient crawling
- [ ] **Visual Crawl Map**: Interactive visualization of crawled pages
- [ ] **Content Classification**: AI-powered content categorization

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help improve KHC Site Crawler:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<p align="center">Made with ❤️ by the Krypto Hashers Community</p> 