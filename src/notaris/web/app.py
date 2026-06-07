"""FastAPI application initialization."""

from fastapi import FastAPI

from notaris.web.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Notaris",
        description="Structured research data extraction from clinical notes.",
        version="0.1.0",
    )
    app.include_router(router)
    return app


app = create_app()
