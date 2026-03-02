from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.translate import router as translate_router


app = FastAPI(title="Doc Generator API", version="1.0.0")
app.include_router(health_router)
app.include_router(translate_router)

