"""Gunicorn configuration for Tariq.lb production hosting."""

import multiprocessing
import os


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# YOLO/PyTorch is memory-heavy, so one worker is safer on small instances.
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
worker_class = "gthread"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "180"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "200"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "40"))
preload_app = os.environ.get("GUNICORN_PRELOAD_APP", "false").lower() in {
    "1",
    "true",
    "yes",
}

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

if workers < 1:
    workers = 1

if os.environ.get("WEB_CONCURRENCY") is None and multiprocessing.cpu_count() == 1:
    threads = max(threads, 2)
