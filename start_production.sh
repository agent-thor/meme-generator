#!/bin/bash

# MemeZap Production Startup Script
# Launches the backend API using Gunicorn with proper timeout settings

echo "Starting MemeZap Backend (Production Mode)..."
echo "============================================="

# Create log directory if it doesn't exist
mkdir -p logs

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "Error: gunicorn is not installed. Please install it with:"
    echo "pip install gunicorn"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please copy .env.example to .env and configure it."
fi

# Start the application with gunicorn
echo "Starting MemeZap Backend with Gunicorn..."
echo "Configuration: gunicorn.conf.py"
echo "Timeout: 300 seconds (5 minutes)"
echo "Workers: Auto-detected based on CPU cores"
echo ""

# Run gunicorn with the configuration file
gunicorn --config gunicorn.conf.py app:app

echo "MemeZap Backend stopped." 