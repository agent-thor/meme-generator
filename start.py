#!/usr/bin/env python3
"""
Simple script to start both the API and webapp servers
"""
import os
import sys
import subprocess
import time
import signal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to track child processes
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    logger.info("Shutting down servers...")
    for process in processes:
        if process.poll() is None:  # If process is still running
            process.terminate()
    sys.exit(0)

def main():
    """Start both servers"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the API server
    logger.info("Starting API server on port 5000...")
    api_process = subprocess.Popen([sys.executable, "app.py"])
    processes.append(api_process)
    
    # Wait for API to start
    logger.info("Waiting for API server to initialize...")
    time.sleep(3)
    
    # Check if API server started successfully
    if api_process.poll() is not None:
        logger.error("API server failed to start. Exiting.")
        sys.exit(1)
    
    # Start the web server
    logger.info("Starting web server on port 8000...")
    webapp_process = subprocess.Popen([sys.executable, "webapp/app.py"])
    processes.append(webapp_process)
    
    # Wait for both processes to complete (they should run indefinitely)
    logger.info("Both servers are running!")
    logger.info("API server: http://localhost:5000")
    logger.info("Web server: http://localhost:8000")
    logger.info("Press Ctrl+C to stop both servers")
    
    try:
        webapp_process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    main() 