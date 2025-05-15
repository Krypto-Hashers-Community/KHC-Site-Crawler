import os
import socket
import subprocess
import sys
import threading
import queue
from queue import Queue
import io
import json
import csv  # Added for CSV export support
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
        # Write to original stdout
        self.old_stdout.write(text)
        
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
                # Only add unique lines to scan_results
                if line not in scan_results:
                    scan_results.append(line)
                    if '✅ Found' in line:
                        found_keywords.append(line)
                    # Queue the line for immediate output
                    output_queue.put(line)

    def flush(self):
        self.old_stdout.flush()
        # Process any remaining content in line buffer
        if self.line_buffer.strip():
            if self.line_buffer not in scan_results:
                scan_results.append(self.line_buffer.strip())
                if '✅ Found' in self.line_buffer:
                    found_keywords.append(self.line_buffer.strip())
                output_queue.put(self.line_buffer.strip())
            self.line_buffer = ""
    
    def getvalue(self):
        return self.buffer.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scan', methods=['POST'])
def start_scan():
    global scan_results, found_keywords, is_scanning
    
    # If already scanning, return error
    if is_scanning:
        return jsonify({'error': 'A scan is already in progress'}), 400
    
    data = request.json
    url = data.get('url', '').strip()
    keywords = data.get('keywords', [])
    max_depth = data.get('max_depth', 3)  # Default to 3 if not provided
    use_proxies = data.get('use_proxies', True)  # Default to True if not provided
    
    if not url:
        return jsonify({'error': 'Please enter a valid URL'}), 400
    
    if not keywords:
        return jsonify({'error': 'Please enter keywords'}), 400
    
    # Reset previous results and state
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
            crawler_main(url, keywords, max_depth=max_depth, use_proxies=use_proxies)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            output_queue.put(error_msg)
        finally:
            # Always restore stdout and update scanning state
            sys.stdout = old_stdout
            is_scanning = False
    
    # Start the crawler thread
    thread = threading.Thread(target=run_crawler_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scan started'})

@app.route('/get_scan_results')
def get_scan_results():
    global is_scanning
    
    # Get any new output from the queue
    new_output = []
    try:
        while not output_queue.empty():
            item = output_queue.get_nowait()
            if item and item.strip():  # Only add non-empty items
                new_output.append(item)
    except queue.Empty:
        pass
    
    # Mark scan as complete if we see the completion message
    if any("[✅] Scan completed!" in line for line in scan_results) or \
       any("[⚡] Turbo crawl finished!" in line for line in scan_results):
        is_scanning = False
    
    # Update found_keywords by scanning scan_results again
    updated_found_keywords = [line for line in scan_results if '✅ Found' in line]
    
    return jsonify({
        'scan_results': scan_results,
        'found_keywords': updated_found_keywords,
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

@app.route('/download_results_csv')
def download_results_csv():
    """
    Export scan results in CSV format.
    Enhancement by: [Yassine Erradouani]
    
    This route provides a user-friendly CSV export with parsed data from
    scan results for easier analysis in spreadsheet applications.
    """
    # Create a CSV file with the results
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # Write header row
    csv_writer.writerow(['Result Type', 'Message', 'URL', 'Keywords Found'])
    
    # Process each result line and extract relevant data
    for line in scan_results:
        result_type = ""
        url = ""
        keywords = ""
        
        # Categorize the result type
        if '✅ Found' in line:
            result_type = "Found Keyword"
            # Extract URL and keyword from lines like "✅ Found 'keyword' at: URL"
            match = line.split("'")
            if len(match) >= 3:
                keywords = match[1]
                url_part = line.split("at: ")
                if len(url_part) > 1:
                    url = url_part[1].strip()
        elif '[🔍]' in line or '[🔎]' in line:
            result_type = "Scanning"
            # Try to extract URL
            url_part = line.split("Scanning ")
            if len(url_part) > 1:
                url = url_part[1].strip()
        elif '[❌]' in line:
            result_type = "Error"
        elif '[⚠️]' in line:
            result_type = "Warning"
        else:
            result_type = "Info"
            
        # Write the processed data to CSV
        csv_writer.writerow([result_type, line, url, keywords])
    
    # Return the CSV file
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='scan_results.csv'
    )

@app.route('/download_results_json')
def download_results_json():
    """
    Export scan results in JSON format.
    Enhancement by: [Yassine Erradouani]
    
    This route provides structured JSON data from scan results for
    integration with other tools or programmatic analysis.
    """
    # Create structured JSON data from the results
    json_data = {
        'scan_summary': {
            'total_results': len(scan_results),
            'keywords_found': len(found_keywords),
            'timestamp': '',  # Could add timestamp if available
        },
        'results': []
    }
    
    # Process each result line
    for line in scan_results:
        result_entry = {
            'raw_message': line,
            'type': '',
            'url': '',
            'keyword': ''
        }
        
        # Categorize and extract data
        if '✅ Found' in line:
            result_entry['type'] = 'keyword_found'
            # Extract URL and keyword
            match = line.split("'")
            if len(match) >= 3:
                result_entry['keyword'] = match[1]
                url_part = line.split("at: ")
                if len(url_part) > 1:
                    result_entry['url'] = url_part[1].strip()
        elif '[🔍]' in line or '[🔎]' in line:
            result_entry['type'] = 'scanning'
            # Try to extract URL
            url_part = line.split("Scanning ")
            if len(url_part) > 1:
                result_entry['url'] = url_part[1].strip()
        elif '[❌]' in line:
            result_entry['type'] = 'error'
        elif '[⚠️]' in line:
            result_entry['type'] = 'warning'
        elif '[✓]' in line or '[✅]' in line:
            result_entry['type'] = 'success'
        else:
            result_entry['type'] = 'info'
            
        json_data['results'].append(result_entry)
    
    # Return the JSON file
    return send_file(
        io.BytesIO(json.dumps(json_data, indent=2).encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name='scan_results.json'
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