"""Production WSGI entrypoint for Tariq.lb."""

from app import create_app


application = create_app()
app = application
