let currentUrl = '';
let currentKeywords = '';
let isScanning = false;
let foundUrls = [];

function showPage(pageId) {
    document.getElementById('introPage').style.display = 'none';
    document.getElementById('urlPage').style.display = 'none';
    document.getElementById('keywordsPage').style.display = 'none';
    document.getElementById('scanningPage').style.display = 'none';
    
    document.getElementById(pageId).style.display = 'block';
}

function showUrlPage() {
    document.getElementById('introPage').style.display = 'none';
    document.getElementById('urlPage').style.display = 'block';
}

function showKeywordsPage() {
    currentUrl = document.getElementById('url').value.trim();
    if (!currentUrl) {
        alert('Please enter a valid URL');
        return;
    }
    document.getElementById('urlPage').style.display = 'none';
    document.getElementById('keywordsPage').style.display = 'block';
}

function startScan() {
    // Get input values
    const url = document.getElementById('url').value.trim();
    const keywords = document.getElementById('keywords').value.trim();
    const maxDepth = document.getElementById('maxDepth').value;
    const useProxies = document.getElementById('useProxies').checked;
    
    // Validate inputs
    if (!url) {
        alert('Please enter a valid URL');
        return;
    }
    if (!keywords) {
        alert('Please enter keywords');
        return;
    }
    
    // Show scanning page
    document.getElementById('keywordsPage').style.display = 'none';
    document.getElementById('scanningPage').style.display = 'block';
    
    // Clear previous results
    document.getElementById('terminalOutput').innerHTML = '';
    document.getElementById('foundKeywords').innerHTML = '';
    
    // Set initial status
    const statusButton = document.getElementById('statusButton');
    statusButton.className = 'status-button status-processing';
    statusButton.textContent = 'Processing';
    
    // Disable start button
    document.getElementById('startScanBtn').disabled = true;
    
    // Start the scan
    isScanning = true;
    fetch('/start_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            keywords: keywords.split(',').map(k => k.trim()),
            max_depth: parseInt(maxDepth),
            use_proxies: useProxies
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            isScanning = false;
            document.getElementById('startScanBtn').disabled = false;
            statusButton.className = 'status-button status-error';
            statusButton.textContent = 'Error';
            return;
        }
        // Start polling for results
        updateResults();
    })
    .catch(error => {
        console.error('Error:', error);
        isScanning = false;
        document.getElementById('startScanBtn').disabled = false;
        statusButton.className = 'status-button status-error';
        statusButton.textContent = 'Error';
    });
}

function startNewScan() {
    document.getElementById('scanningPage').style.display = 'none';
    document.getElementById('urlPage').style.display = 'block';
    document.getElementById('url').value = '';
    document.getElementById('keywords').value = '';
    document.getElementById('keywordsCounter').textContent = '0';
    currentUrl = '';
    currentKeywords = '';
    isScanning = false;
    foundUrls = [];
    document.getElementById('openAllUrlsBtn').style.display = 'none';
}

function formatTerminalLine(line) {
    let className = 'terminal-line';
    
    // Add specific classes based on message type
    if (line.includes('[❌]')) {
        className += ' error-message';
    } else if (line.includes('[⚠️]')) {
        className += ' warning-message';
    } else if (line.includes('[✓]') || line.includes('[✅]')) {
        className += ' success-message';
    } else if (line.includes('[🔎]') || line.includes('[🔍]') || line.includes('[📊]')) {
        className += ' info-message';
    } else if (line.includes('[🔀]') || line.includes('[🔄]')) {
        className += ' system-message';
    } else if (line.includes('Fast Scan') || line.includes('Fast scan')) {
        className += ' fast-scan-message';
    } else if (line.includes('[⚡]') || line.includes('TURBO')) {
        className += ' turbo-message';
    }
    
    return `<div class="${className}">${line}</div>`;
}

function updateResults() {
    if (!isScanning) return;
    
    fetch('/get_scan_results')
        .then(response => response.json())
        .then(data => {
            // Update terminal output
            const terminalOutput = document.getElementById('terminalOutput');
            if (data.new_output && data.new_output.length > 0) {
                data.new_output.forEach(line => {
                    if (line.trim()) {  // Only add non-empty lines
                        const lineDiv = document.createElement('div');
                        lineDiv.className = 'terminal-line';
                        lineDiv.textContent = line;
                        terminalOutput.appendChild(lineDiv);
                    }
                });
                // Always scroll to bottom after adding new content
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }
            
            // Update found keywords
            const keywordsDiv = document.getElementById('foundKeywords');
            if (data.found_keywords && data.found_keywords.length > 0) {
                keywordsDiv.innerHTML = '';  // Clear existing content
                const uniqueUrls = new Set();  // Track unique URLs
                
                data.found_keywords.forEach(keyword => {
                    if (keyword.trim()) {  // Only add non-empty keywords
                        const keywordDiv = document.createElement('div');
                        keywordDiv.className = 'found-keyword';
                        
                        // Extract URL from the keyword line
                        const urlMatch = keyword.match(/at: (https?:\/\/[^\s]+)/);
                        if (urlMatch) {
                            const url = urlMatch[1];
                            uniqueUrls.add(url);  // Add to unique URLs set
                            
                            // Create clickable link
                            const link = document.createElement('a');
                            link.href = url;
                            link.target = '_blank';
                            link.textContent = keyword;
                            link.style.color = '#4a90e2';
                            link.style.textDecoration = 'none';
                            link.style.cursor = 'pointer';
                            
                            // Add hover effect
                            link.addEventListener('mouseover', () => {
                                link.style.textDecoration = 'underline';
                            });
                            link.addEventListener('mouseout', () => {
                                link.style.textDecoration = 'none';
                            });
                            
                            keywordDiv.appendChild(link);
                        } else {
                            keywordDiv.textContent = keyword;
                        }
                        
                        keywordsDiv.appendChild(keywordDiv);
                    }
                });
                
                // Update keyword counter
                const keywordsCounter = document.getElementById('keywordsCounter');
                keywordsCounter.textContent = uniqueUrls.size;
                
                // Show/hide "Open All URLs" button based on found URLs
                const openAllUrlsBtn = document.getElementById('openAllUrlsBtn');
                if (uniqueUrls.size > 0) {
                    openAllUrlsBtn.style.display = 'block';
                    // Update the button's onclick handler with current URLs
                    openAllUrlsBtn.onclick = () => {
                        uniqueUrls.forEach(url => window.open(url, '_blank'));
                    };
                } else {
                    openAllUrlsBtn.style.display = 'none';
                }
            }
            
            // Update scanning status
            isScanning = data.is_scanning;
            const statusButton = document.getElementById('statusButton');
            
            if (!isScanning) {
                document.getElementById('startScanBtn').disabled = false;
                statusButton.className = 'status-button status-complete';
                statusButton.textContent = 'Completed';
            } else {
                statusButton.className = 'status-button status-processing';
                statusButton.textContent = 'Processing';
            }
            
            // Continue polling if still scanning
            if (isScanning) {
                // Use a shorter interval for more responsive updates
                setTimeout(updateResults, 500);
            }
        })
        .catch(error => {
            console.error('Error fetching results:', error);
            // Continue polling even if there's an error, but with a longer interval
            if (isScanning) {
                setTimeout(updateResults, 1000);
            }
        });
}

// New function to update found keywords display
function updateFoundKeywords(foundKeywordData) {
    const foundKeywords = document.getElementById('foundKeywords');
    foundUrls = [];
    
    let keywordHtml = '<div class="found-keywords-note">Double-click on any result to open the link in a new tab</div>';
    
    keywordHtml += foundKeywordData.map(line => {
        // Extract URL and keyword
        const match = line.match(/✅ Found '(.+?)' at: (.+)/);
        if (match) {
            const keyword = match[1];
            const url = match[2];
            
            // Add to foundUrls array
            if (!foundUrls.includes(url)) {
                foundUrls.push(url);
            }
            
            // Return formatted HTML with clickable link
            return `<div class="found-keyword" ondblclick="window.open('${url}', '_blank')" title="Double-click to open">
                Found <span class="found-keyword-term">${keyword}</span> at: 
                <span class="found-keyword-url">${url}</span>
            </div>`;
        }
        return `<div class="found-keyword">${line}</div>`;
    }).join('');
    
    foundKeywords.innerHTML = keywordHtml;
    
    // Update the keywords counter with the unique URLs count
    const keywordsCounter = document.getElementById('keywordsCounter');
    keywordsCounter.textContent = foundUrls.length.toString();
    // Add pulse animation when the count changes
    keywordsCounter.style.animation = 'none';
    setTimeout(() => {
        keywordsCounter.style.animation = 'pulse 1s ease-in-out';
    }, 10);
    
    // Show the open all URLs button if we have URLs
    if (foundUrls.length > 0) {
        document.getElementById('openAllUrlsBtn').style.display = 'block';
    }
}

function openAllFoundUrls() {
    if (foundUrls.length === 0) return;
    
    // Ask for confirmation if there are many URLs
    if (foundUrls.length > 5) {
        const confirmOpen = confirm(`Are you sure you want to open ${foundUrls.length} URLs in new tabs?`);
        if (!confirmOpen) return;
    }
    
    // Open each URL in a new tab
    foundUrls.forEach(url => {
        window.open(url, '_blank');
    });
}

function downloadResults() {
    // Get the selected export format
    const format = document.getElementById('exportFormat').value;
    
    // Choose the appropriate endpoint based on the format
    let endpoint = '/download_results';
    
    if (format === 'csv') {
        endpoint = '/download_results_csv';
    } else if (format === 'json') {
        endpoint = '/download_results_json';
    }
    
    // Navigate to the download URL
    window.location.href = endpoint;
}

// Add a function to show a notice about TURBO mode
function showTurboModeNotice() {
    // Create a notice element
    const notice = document.createElement('div');
    notice.className = 'turbo-notice';
    notice.innerHTML = `
        <div style="background-color: rgba(255, 51, 102, 0.1); border: 2px solid #ff3366; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
            <h5 style="color: #ff3366; margin-top: 0;"><span style="font-size: 1.2em;">⚡</span> Want to scan ALL pages?</h5>
            <p>You're currently using "<span id="currentMode"></span>" mode.</p>
            <p>To scan all pages and sub-pages without limits, select <strong style="color: #ff3366;">⚡ TURBO</strong> mode in the dropdown.</p>
            <button class="btn btn-sm" style="background-color: #ff3366; color: white; margin-top: 5px;" onclick="document.getElementById('turboNotice').style.display='none';">Got it!</button>
        </div>
    `;
    
    // Add the notice to the page
    const container = document.getElementById('keywordsPage').querySelector('.card-body');
    const existingNotice = document.getElementById('turboNotice');
    
    if (!existingNotice) {
        notice.id = 'turboNotice';
        container.insertBefore(notice, container.firstChild);
    }
    
    // Update the current mode text
    const modeSelect = document.getElementById('maxDepth');
    const selectedOption = modeSelect.options[modeSelect.selectedIndex].text;
    document.getElementById('currentMode').textContent = selectedOption;
}

// Add event listeners when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add click handler for start scan button
    document.getElementById('startScanBtn').addEventListener('click', startScan);
    
    // Add enter key handler for the keyword input
    document.getElementById('url').addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            
            // If keywords are filled, start the scan
            if (document.getElementById('keywords').value.trim()) {
                startScan();
            } else {
                // Otherwise focus on keywords field
                document.getElementById('keywords').focus();
            }
        }
    });
    
    // Add enter key handler for the keyword input
    document.getElementById('keywords').addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            startScan();
        }
    });

    // Fix the openAllUrlsBtn event handling
    document.getElementById('openAllUrlsBtn').addEventListener('click', openAllFoundUrls);
    
    // Add change handler for the maxDepth select to manage proxy checkbox
    document.getElementById('maxDepth').addEventListener('change', function() {
        const maxDepth = this.value;
        const proxiesCheckbox = document.getElementById('useProxies');
        const proxiesLabel = proxiesCheckbox.nextElementSibling;
        const proxiesHint = proxiesLabel.nextElementSibling;
        
        // Disable proxies for Fast Scan and Turbo mode
        if (maxDepth === '0' || maxDepth === '-1') {
            proxiesCheckbox.disabled = true;
            proxiesLabel.style.opacity = '0.5';
            proxiesHint.style.opacity = '0.5';
            
            // Show specific message based on mode
            if (maxDepth === '0') {
                proxiesHint.textContent = 'Proxies disabled in Fast Scan mode (single page scan).';
            } else {
                proxiesHint.textContent = 'Proxies disabled in Turbo mode for maximum speed.';
            }
        } else {
            proxiesCheckbox.disabled = false;
            proxiesLabel.style.opacity = '1';
            proxiesHint.style.opacity = '1';
            proxiesHint.textContent = 'Slower but may work on sites that block crawlers.';
        }
        
        // Update the notice
        const currentOption = this.options[this.selectedIndex].text;
        if (document.getElementById('currentMode')) {
            document.getElementById('currentMode').textContent = currentOption;
        }
    });
    
    // Initialize proxy state based on current depth selection
    document.getElementById('maxDepth').dispatchEvent(new Event('change'));
    
    // Show Turbo mode notice when the keywords page is shown
    // Wait until elements are available
    setTimeout(function() {
        const urlInput = document.getElementById('url');
        if (urlInput) {
            urlInput.addEventListener('blur', function() {
                if (this.value.trim()) {
                    showTurboModeNotice();
                }
            });
        }
    }, 1000);
}); 