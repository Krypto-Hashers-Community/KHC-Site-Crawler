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
    currentKeywords = document.getElementById('keywords').value.trim();
    if (!currentKeywords) {
        alert('Please enter keywords');
        return;
    }

    // Get max depth value
    const maxDepth = document.getElementById('maxDepth').value;
    
    // Get proxy option
    const useProxies = document.getElementById('useProxies').checked;
    
    document.getElementById('keywordsPage').style.display = 'none';
    document.getElementById('scanningPage').style.display = 'block';

    // Update scan info
    document.getElementById('scanInfo').innerHTML = `
        <strong>Website:</strong> ${currentUrl}<br>
        <strong>Keywords:</strong> ${currentKeywords}<br>
        <strong>Crawl Depth:</strong> ${maxDepth}<br>
        <strong>Using Proxies:</strong> ${useProxies ? 'Yes' : 'No'}
    `;
    
    // Clear previous results
    document.getElementById('terminalOutput').innerHTML = '';
    document.getElementById('foundKeywords').innerHTML = '';
    document.getElementById('keywordsCounter').textContent = '0';
    foundUrls = [];
    document.getElementById('openAllUrlsBtn').style.display = 'none';
    
    // Set initial status
    const statusButton = document.getElementById('statusButton');
    statusButton.className = 'status-button status-processing';
    statusButton.textContent = 'Processing';
    
    // Start the scan
    isScanning = true;
    fetch('/start_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: currentUrl,
            keywords: currentKeywords.split(',').map(k => k.trim()),
            max_depth: parseInt(maxDepth),
            use_proxies: useProxies
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            isScanning = false;
            return;
        }
        // Start polling for results
        pollResults();
    })
    .catch(error => {
        console.error('Error:', error);
        isScanning = false;
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
    }
    
    return `<div class="${className}">${line}</div>`;
}

function pollResults() {
    if (!isScanning) return;
    
    fetch('/get_scan_results')
        .then(response => response.json())
        .then(data => {
            // Update terminal output incrementally
            const terminalOutput = document.getElementById('terminalOutput');
            
            // Clear and rebuild if there's a significant change
            if (Math.abs(data.scan_results.length - terminalOutput.childElementCount) > 10) {
                terminalOutput.innerHTML = data.scan_results
                    .map(line => formatTerminalLine(line))
                    .join('');
            }
            // Otherwise just append new output
            else if (data.new_output && data.new_output.length > 0) {
                let newContent = '';
                data.new_output.forEach(text => {
                    // Split text into lines and add each line
                    text.split('\n').forEach(line => {
                        if (line.trim()) {
                            newContent += formatTerminalLine(line);
                        }
                    });
                });
                
                // Append the new content
                if (newContent) {
                    // Preserve scroll position
                    const wasAtBottom = terminalOutput.scrollTop + terminalOutput.clientHeight >= terminalOutput.scrollHeight - 10;
                    
                    // Append content
                    terminalOutput.innerHTML += newContent;
                    
                    // Auto-scroll if we were at the bottom
                    if (wasAtBottom) {
                        terminalOutput.scrollTop = terminalOutput.scrollHeight;
                    }
                }
            }

            // Update found keywords
            const foundKeywords = document.getElementById('foundKeywords');
            
            if (data.found_keywords && data.found_keywords.length > 0) {
                // Extract URLs and update foundUrls array
                foundUrls = [];
                
                let keywordHtml = '<div class="found-keywords-note">Double-click on any result to open the link in a new tab</div>';
                
                keywordHtml += data.found_keywords.map(line => {
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

            // Update status button
            const statusButton = document.getElementById('statusButton');
            
            // Check for completion or errors
            if (!data.is_scanning || data.scan_results.some(line => line.includes("[✅] Scan completed!"))) {
                if (data.scan_results.some(line => line.includes("Error"))) {
                    statusButton.className = 'status-button status-error';
                    statusButton.textContent = 'Error';
                } else {
                    statusButton.className = 'status-button status-complete';
                    statusButton.textContent = 'Completed';
                }
                isScanning = false;
            } else {
                statusButton.className = 'status-button status-processing';
                statusButton.textContent = 'Processing';
                // Continue polling only if still scanning
                setTimeout(pollResults, 500); // Poll more frequently (500ms)
            }
        })
        .catch(error => {
            console.error('Error polling results:', error);
            const statusButton = document.getElementById('statusButton');
            statusButton.className = 'status-button status-error';
            statusButton.textContent = 'Error';
            isScanning = false;
        });
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
    window.location.href = '/download_results';
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
}); 