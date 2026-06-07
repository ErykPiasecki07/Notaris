"""HTTP routes for the Notaris web app."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report application health for local checks and tests."""
    return {"status": "ok"}
