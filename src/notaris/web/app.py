"""FastAPI application initialization."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from notaris.web.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Notaris",
        description="Structured research data extraction from clinical notes.",
        version="0.1.0",
    )
    app.include_router(router)

    secret_key = os.getenv("NOTARIS_SECRET_KEY", "notaris-demo-secret-key")
    app.add_middleware(SessionMiddleware, secret_key=secret_key)

    static_path = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    return app


app = create_app()
