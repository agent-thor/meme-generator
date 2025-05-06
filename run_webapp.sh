#!/bin/bash
# Start the Web Application on port 8000

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Source the .env file if it exists
echo "Loading configuration from .env file..."

echo "Starting Web Application on port 8000..."
python webapp/app.py 