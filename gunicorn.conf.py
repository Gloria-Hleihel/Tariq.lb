"""Gunicorn production settings for Tariq.lb."""

import multiprocessing
import os


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "0")) or max(
    2,
    min(4, multiprocessing.cpu_count()),
)
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

preload_app = os.environ.get("GUNICORN_PRELOAD_APP", "0").lower() in {
    "1",
    "true",
    "yes",
}
