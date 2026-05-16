from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check — process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    """Readiness check — DB is reachable."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
