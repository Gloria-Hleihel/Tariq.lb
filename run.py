import os

from app import create_app
import config

app = create_app()


if __name__ == "__main__":
    debug_enabled = os.environ.get("FLASK_DEBUG", "0") == "1"
    if config.IS_PRODUCTION and debug_enabled:
        raise RuntimeError("Do not run Flask debug mode in production.")

    app.run(
        debug=debug_enabled,
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_RUN_PORT", "5000")),
    )
