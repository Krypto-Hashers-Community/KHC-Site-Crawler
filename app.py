import os
import socket
import subprocess
import sys
import threading
import queue
from queue import Queue
import io
from flask import Flask, render_template, request, jsonify, send_file

# Import the crawler module
import crawler

app = Flask(__name__)

# Global variables for scan state
scan_results = []
found_keywords = []
is_scanning = False
output_queue = queue.Queue()

def find_available_port(start_port=5000, max_port=6000):
    """Find an available port in the given range."""
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No available ports found in the specified range")

def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            subprocess.run(['taskkill', '/F', '/PID', str(port)], capture_output=True)
        else:  # Unix-like systems (Linux, macOS)
            subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True)
            subprocess.run(['kill', '-9', str(port)], capture_output=True)
    except:
        pass  # Ignore errors if no process is found

class OutputCapture:
    def __init__(self):
        self.buffer = io.StringIO()
        self.old_stdout = sys.stdout
        self.line_buffer = ""
    
    def write(self, text):
        # Write to original stdout and buffer
        self.buffer.write(text)
        self.old_stdout.write(text)
        
        # Always queue the raw text for immediate output
        output_queue.put(text)
        
        # Add to line buffer and check for full lines
        self.line_buffer += text
        lines_to_process = []
        
        # If we have complete lines, process them
        if '\n' in self.line_buffer:
            parts = self.line_buffer.split('\n')
            # The last part might be an incomplete line
            self.line_buffer = parts[-1]
            # All other parts are complete lines
            lines_to_process = [part for part in parts[:-1] if part.strip()]
        
        # Process complete lines for scan_results and found_keywords
        for line in lines_to_process:
            if line.strip():
                scan_results.append(line)
                if '✅ Found' in line:
                    found_keywords.append(line)

    def flush(self):
        self.buffer.flush()
        self.old_stdout.flush()
        # Process any remaining content in line buffer
        if self.line_buffer.strip():
            scan_results.append(self.line_buffer.strip())
            if '✅ Found' in self.line_buffer:
                found_keywords.append(self.line_buffer.strip())
            self.line_buffer = ""
    
    def getvalue(self):
        return self.buffer.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scan', methods=['POST'])
def start_scan():
    global scan_results, found_keywords, is_scanning
    
    data = request.json
    url = data.get('url', '').strip()
    keywords = data.get('keywords', [])
    max_depth = data.get('max_depth', 3)  # Default to 3 if not provided
    use_proxies = data.get('use_proxies', True)  # Default to True if not provided
    
    if not url:
        return jsonify({'error': 'Please enter a valid URL'}), 400
    
    if not keywords:
        return jsonify({'error': 'Please enter keywords'}), 400
    
    # Reset previous results
    scan_results = []
    found_keywords = []
    is_scanning = True
    
    # Create a thread to run the crawler
    def run_crawler_thread():
        try:
            # Redirect stdout to capture output
            old_stdout = sys.stdout
            sys.stdout = OutputCapture()
            
            # Run the crawler with the correct parameters
            from crawler import main as crawler_main
            
            # Run the crawler
            crawler_main(url, keywords, max_depth=max_depth, use_proxies=use_proxies)
            
            # Restore stdout
            sys.stdout = old_stdout
            is_scanning = False
            
        except Exception as e:
            output_queue.put(f"Error: {str(e)}")
            is_scanning = False
    
    # Start the crawler thread
    thread = threading.Thread(target=run_crawler_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scan started'})

@app.route('/get_scan_results')
def get_scan_results():
    global is_scanning
    
    # Mark scan as complete if we see the completion message or error messages about site access
    if any("[✅] Scan completed!" in line for line in scan_results) or \
       any("[⚡] Turbo crawl finished!" in line for line in scan_results) or \
       any("[⚠️] The website might be blocking crawlers" in line for line in scan_results):
        is_scanning = False
    
    # Get any new output from the queue (increased limit for Turbo mode)
    new_output = []
    max_queue_items = 200  # Increased from 50 to handle more output
    count = 0
    
    while not output_queue.empty() and count < max_queue_items:
        try:
            item = output_queue.get_nowait()
            new_output.append(item)
            count += 1
        except queue.Empty:
            break
    
    # Update found_keywords by scanning scan_results again
    # This ensures we don't miss any findings, especially in Turbo mode
    updated_found_keywords = [line for line in scan_results if '✅ Found' in line]
    
    return jsonify({
        'scan_results': scan_results,
        'found_keywords': updated_found_keywords,
        'is_scanning': is_scanning,
        'new_output': new_output,
        'queue_size': output_queue.qsize()  # Send queue size for debugging
    })

@app.route('/download_results')
def download_results():
    # Create a text file with the results
    results_text = '\n'.join(scan_results)
    return send_file(
        io.BytesIO(results_text.encode()),
        mimetype='text/plain',
        as_attachment=True,
        download_name='scan_results.txt'
    )

if __name__ == '__main__':
    # Try to use port 5000 first
    try:
        port = find_available_port(5000, 5000)
    except RuntimeError:
        # If port 5000 is not available, find any available port
        port = find_available_port(5001, 6000)
    
    print(f"Starting server on port {port}")
    app.run(debug=True, port=port) 