"""Compatibility entrypoint for QueryShield FastAPI app.

Canonical API implementation lives in `queryshield.app.api`.
This module keeps `uvicorn queryshield.api.main:app` working.
"""

from __future__ import annotations

from queryshield.app.api import app

__all__ = ["app"]

