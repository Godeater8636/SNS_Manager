from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.v1.router import api_router
from app.api.v1.media import router as media_router
from app.core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing required here (DB created by Alembic migrations)
    yield
    # Shutdown: cleanup connections
    from app.database import engine
    await engine.dispose()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import logging
    logging.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "内部エラーが発生しました"}},
    )


app.include_router(api_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")

# ローカルストレージのファイルを /media/* で配信（S3 未設定時）
if not settings.AWS_ACCESS_KEY_ID:
    _media_path = Path(settings.LOCAL_STORAGE_PATH).resolve()
    _media_path.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(_media_path)), name="media")


@app.get("/healthz")
async def healthz():
    import redis.asyncio as aioredis
    db_ok = True
    redis_ok = True
    try:
        from app.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "version": settings.APP_VERSION,
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
