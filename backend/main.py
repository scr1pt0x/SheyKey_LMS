from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.core.config import settings
from backend.core.redis_client import close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Islamic Finance LMS API...")
    await get_redis()
    yield
    logger.info("Shutting down...")
    await close_redis()


app = FastAPI(
    title="Islamic Finance LMS",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/api/openapi.json" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
from backend.api.auth import router as auth_router
from backend.api.calendar import router as calendar_router
from backend.api.clients import router as clients_router
from backend.api.deals import router as deals_router
from backend.api.director import router as director_router
from backend.api.documents import router as documents_router
from backend.api.generate import router as generate_router
from backend.api.notifications import router as notifications_router
from backend.api.import_data import router as import_router
from backend.api.profit import router as profit_router
from backend.api.payments import router as payments_router
from backend.api.sb import router as sb_router

app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(deals_router)
app.include_router(payments_router)
app.include_router(documents_router)
app.include_router(generate_router)
app.include_router(calendar_router)
app.include_router(sb_router)
app.include_router(director_router)
app.include_router(notifications_router)
app.include_router(import_router)
app.include_router(profit_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}
