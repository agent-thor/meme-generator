#!/bin/bash

# Start the API server in the background
echo "Starting meme generation API server..."
hypercorn app:app --bind 0.0.0.0:5000 --workers 4 &
API_PID=$!

# Wait a moment for the API to start
sleep 2

# Start the web server
echo "Starting web server..."
hypercorn webapp.app:app --bind 0.0.0.0:8000 --workers 4

# If the web server exits, kill the API server
kill $API_PID 