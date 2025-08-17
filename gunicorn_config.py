# Gunicorn configuration file for BenchstayV2 production deployment

# Bind to Unix socket
bind = 'unix:/opt/BenchstayV2/benchstay.sock'

# Worker processes
workers = 3  # Recommended: 2-4 x number of CPU cores
worker_class = 'gevent'  # Use gevent for async workers
threads = 2  # Number of threads per worker

# Timeout settings
timeout = 60  # Seconds before a worker is killed and restarted
keepalive = 5  # Seconds to keep idle connections open

# Server mechanics
max_requests = 1000  # Restart workers after handling this many requests
max_requests_jitter = 50  # Add randomness to max_requests to avoid all workers restarting at once

# Logging
logfile = '/opt/BenchstayV2/logs/gunicorn.log'
loglevel = 'info'
accesslog = '/opt/BenchstayV2/logs/access.log'
errorlog = '/opt/BenchstayV2/logs/error.log'
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'benchstay_gunicorn'

# Server hooks
def on_starting(server):
    # Code to run when server starts
    pass

def on_reload(server):
    # Code to run when server reloads
    pass

def post_fork(server, worker):
    # Code to run after a worker has been forked
    pass

def pre_fork(server, worker):
    # Code to run before forking a worker
    pass

def pre_exec(server):
    # Code to run just before exec()'ing a new binary
    pass

def when_ready(server):
    # Code to run when server is ready to accept connections
    pass

def worker_int(worker):
    # Code to run when a worker receives SIGINT
    pass

def worker_abort(worker):
    # Code to run when a worker receives SIGABRT
    pass

def worker_exit(server, worker):
    # Code to run when a worker exits
    pass