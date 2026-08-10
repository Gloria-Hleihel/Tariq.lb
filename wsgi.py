"""Production WSGI entry point for Tariq.lb."""

from app import create_app


application = create_app()
app = application
