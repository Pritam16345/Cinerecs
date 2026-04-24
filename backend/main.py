"""
CineRecs API — Main Entry Point.
FastAPI with lifespan, CORS, and FAISS.
"""

import os, time, logging, traceback
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import get_pool, initialize_schema, close_pool
from services.redis_service import get_redis, close_redis, ping as ping_redis
from services.faiss_service import FAISSService
from routers.movies import router as movies_router, set_faiss_service as movies_set_faiss
from routers.auth import router as auth_router
from routers.recommend import router as recommend_router, set_faiss_service as recommend_set_faiss
from routers.ratings import router as ratings_router
from routers.watchlist import router as watchlist_router

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("cinerecs")

# Services
faiss_service = FAISSService()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown."""
    logger.info("Starting CineRecs API...")

    # DB
    try:
        await get_pool(); await initialize_schema()
        logger.info("✓ DB Ready")
    except Exception as e: logger.error(f"✗ DB Fail: {e}")

    # Redis
    try:
        if await get_redis() and await ping_redis(): logger.info("✓ Redis Ready")
    except Exception as e: logger.warning(f"⚠ Redis Fail: {e}")

    # FAISS
    try:
        faiss_service.load_model()
        if faiss_service.load_from_r2(): logger.info("✓ FAISS Ready")
    except Exception as e: logger.warning(f"⚠ FAISS Fail: {e}")

    # Inject
    movies_set_faiss(faiss_service)
    recommend_set_faiss(faiss_service)

    yield

    logger.info("Shutting down...")
    await close_pool(); await close_redis()
    logger.info("Shutdown complete")


app = FastAPI(
    title="CineRecs API",
    version="3.0.0",
    description="Hybrid movie recommendation system.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Response time and request logging."""
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{ms}ms"

    if request.url.path not in ("/", "/health", "/favicon.ico"):
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
    return response


# Routes
app.include_router(movies_router)
app.include_router(auth_router)
app.include_router(recommend_router)
app.include_router(ratings_router)
app.include_router(watchlist_router)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "CineRecs API",
        "version": "3.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """System health status."""
    db_ok, redis_ok = False, False
    try:
        p = await get_pool(); await p.fetchval("SELECT 1"); db_ok = True
    except: pass
    try: redis_ok = await ping_redis()
    except: pass
    
    faiss_ok = faiss_service.is_loaded()
    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "faiss": "loaded" if faiss_ok else "not_loaded",
    }


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Global 500 handler."""
    logger.error(f"Error on {request.url.path}: {traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
