from fastapi import FastAPI

from app.api import routes_health
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(routes_health.router)
