"""Health check and status endpoints."""

from fastapi import APIRouter

from betting_bot.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}


@router.get("/version")
async def version_info():
    """Return application version information."""
    settings = get_settings()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }
