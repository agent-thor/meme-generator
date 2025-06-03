# Simple Gunicorn configuration for fast startup
import os

# Basic server settings
bind = "0.0.0.0:5003"
workers = 1
worker_class = "sync"  # Simple sync worker
timeout = 300  # 5 minutes timeout
keepalive = 2

# Logging
loglevel = "info"
errorlog = "-"  # Log to stdout/stderr
accesslog = "-"  # Log to stdout/stderr

# Process settings
preload_app = True
daemon = False 