"""Local development server entry point."""

import uvicorn


def main() -> None:
    """Run the Notaris app with Uvicorn for local development."""
    uvicorn.run(
        "notaris.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
