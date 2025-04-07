let currentUrl = '';
let currentKeywords = '';
let isScanning = false;

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

    document.getElementById('keywordsPage').style.display = 'none';
    document.getElementById('scanningPage').style.display = 'block';

    // Update scan info
    document.getElementById('scanInfo').innerHTML = `
        <strong>Website:</strong> ${currentUrl}<br>
        <strong>Keywords:</strong> ${currentKeywords}
    `;

    // Clear previous results
    document.getElementById('terminalOutput').innerHTML = '';
    document.getElementById('foundKeywords').innerHTML = '';

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
            keywords: currentKeywords.split(',').map(k => k.trim())
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
    currentUrl = '';
    currentKeywords = '';
    isScanning = false;
}

function pollResults() {
    if (!isScanning) return;
    
    fetch('/get_scan_results')
        .then(response => response.json())
        .then(data => {
            // Update terminal output
            const terminalOutput = document.getElementById('terminalOutput');
            terminalOutput.innerHTML = data.scan_results
                .map(line => `<div class="terminal-line">${line}</div>`)
                .join('');

            // Update found keywords
            const foundKeywords = document.getElementById('foundKeywords');
            foundKeywords.innerHTML = data.found_keywords
                .map(line => `<div class="found-keyword">${line}</div>`)
                .join('');

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
                setTimeout(pollResults, 1000);
            }

            // Scroll to bottom
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
            foundKeywords.scrollTop = foundKeywords.scrollHeight;
        })
        .catch(error => {
            console.error('Error polling results:', error);
            const statusButton = document.getElementById('statusButton');
            statusButton.className = 'status-button status-error';
            statusButton.textContent = 'Error';
            isScanning = false;
        });
}

function downloadResults() {
    window.location.href = '/download_results';
} 