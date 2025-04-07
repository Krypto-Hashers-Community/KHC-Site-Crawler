#!/bin/bash

# Function to find and kill process on a port
kill_port() {
    local port=$1
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        lsof -ti :$port | xargs kill -9 2>/dev/null
    else
        # Linux
        fuser -k $port/tcp 2>/dev/null
    fi
}

# Kill any existing processes on ports 5000-5005
for port in {5000..5005}; do
    kill_port $port
done

# Start the Flask application
python3 app.py 