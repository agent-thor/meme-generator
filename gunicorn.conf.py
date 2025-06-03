# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5003"
backlog = 2048

# Worker processes - reduced for faster startup with heavy models
# Each worker needs to load models, so fewer workers = faster startup
workers = 1  # Start with 1 worker for faster startup
worker_class = "gthread"  # Use threads instead of processes for better model sharing
threads = 4  # Handle multiple requests with threads (shares models)
worker_connections = 1000

# Timeout settings - increased for model loading
timeout = 300  # 5 minutes for worker timeout (allows model download/loading)
keepalive = 2
graceful_timeout = 120  # 2 minutes for graceful shutdown

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "memezap-backend"

# Server mechanics
preload_app = True  # Load application code before forking workers
daemon = False
pidfile = "logs/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Worker process settings
worker_tmp_dir = "/dev/shm"  # Use memory for worker temp files if available

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting MemeZap Backend Server")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading MemeZap Backend Server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("MemeZap Backend Server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Forking worker %s (this may take time due to model loading)...", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker %s forked, initializing models...", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker %s fully initialized and ready!", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal") 