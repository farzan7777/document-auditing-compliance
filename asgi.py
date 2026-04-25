"""
ASGI entrypoint for Docker / Hugging Face Spaces.

Use `uvicorn asgi:app` so the loaded module is `asgi`, not `app.main`, which avoids
edge cases where the container workdir or import path is confused with the `app`
Python package.
"""

from app.main import app

__all__ = ["app"]
