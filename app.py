from flask import Flask, render_template, request, jsonify, send_file
import os
from crawler import main as run_crawler
import threading
import io
import sys
from io import StringIO
import socket
import subprocess
import queue

app = Flask(__name__)

# Global variables to store scan results
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
        self.buffer = StringIO()
        self.old_stdout = sys.stdout

    def write(self, text):
        self.buffer.write(text)
        self.old_stdout.write(text)
        output_queue.put(text)
        # Split the text into lines and add to scan_results
        for line in text.split('\n'):
            if line.strip():
                scan_results.append(line)
                if '✅ Found' in line:
                    found_keywords.append(line)

    def flush(self):
        self.buffer.flush()
        self.old_stdout.flush()

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
            
            # Run the crawler
            run_crawler(url, keywords)
            
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
    
    # Mark scan as complete if we see the completion message
    if any("[✅] Scan completed!" in line for line in scan_results):
        is_scanning = False
    
    # Get any new output from the queue
    new_output = []
    while not output_queue.empty():
        try:
            new_output.append(output_queue.get_nowait())
        except queue.Empty:
            break
    
    return jsonify({
        'scan_results': scan_results,
        'found_keywords': found_keywords,
        'is_scanning': is_scanning,
        'new_output': new_output
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