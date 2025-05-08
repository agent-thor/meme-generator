#!/bin/bash
# Start the Meme Generator API

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Source the .env file if it exists
echo "Loading configuration from .env file..."

echo "Starting Meme Generator API on port $(grep APP_PORT .env | cut -d= -f2)..."
python app.py
echo "Starting Meme Generator Webapp on port $(grep PORT .env | cut -d= -f2)..."
python webapp/app.py
