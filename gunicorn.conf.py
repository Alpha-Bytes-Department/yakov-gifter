import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

bind = '0.0.0.0:8000'
backlog = 2048

accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = 'ezlain_backend'
daemon = False
preload_app = True

max_requests = 1000
max_requests_jitter = 50
