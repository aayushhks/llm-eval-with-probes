from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_health, routes_runs
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("app_started", environment=settings.environment)
    yield
    logger.info("app_stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

_extra_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins,
    allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes_health.router)
app.include_router(routes_runs.router)
