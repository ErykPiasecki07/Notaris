"""FastAPI application initialization."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from notaris.web.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Notaris",
        description="Structured research data extraction from clinical notes.",
        version="0.1.0",
    )
    app.include_router(router)

    static_path = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    return app


app = create_app()
