#!/bin/bash

# MemeZap Startup Script
# Launches both API backend and Web frontend

echo "Starting MemeZap Services..."
echo "=============================="

# Create log directory if it doesn't exist
mkdir -p logs

# Start the API server (backend) in the background
echo "Starting API Server (Backend)..."
python app.py > logs/api_server.log 2>&1 &
API_PID=$!
echo "API Server started with PID: $API_PID"

# Give the API server a moment to start up
sleep 2

# Start the Web interface (frontend) in the background
echo "Starting Web Interface (Frontend)..."
python webapp/app.py > logs/web_interface.log 2>&1 &
WEB_PID=$!
echo "Web Interface started with PID: $WEB_PID"

echo ""
echo "MemeZap is now running!"
echo "API Server: http://localhost:5000"
echo "Web Interface: http://localhost:8000"
echo ""
echo "To stop the services, press Ctrl+C"
echo "API logs: logs/api_server.log"
echo "Web logs: logs/web_interface.log"
echo ""

# Save PIDs to a file for cleanup
echo "$API_PID $WEB_PID" > .memezap_pids

# Handle cleanup on script termination
cleanup() {
    echo ""
    echo "Shutting down MemeZap services..."
    
    # Kill the processes if they're still running
    if ps -p $API_PID > /dev/null; then
        echo "Stopping API Server..."
        kill $API_PID
    fi
    
    if ps -p $WEB_PID > /dev/null; then
        echo "Stopping Web Interface..."
        kill $WEB_PID
    fi
    
    # Remove PID file
    rm -f .memezap_pids
    
    echo "MemeZap services stopped."
    exit 0
}

# Set the cleanup function to run on script termination
trap cleanup INT TERM

# Keep the script running to allow for Ctrl+C to work
# and to view the logs
echo "Tailing logs (press Ctrl+C to stop)..."
echo "=============================="
tail -f logs/api_server.log logs/web_interface.log 