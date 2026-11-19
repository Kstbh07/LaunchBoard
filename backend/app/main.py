from contextlib import asynccontextmanager
from typing import Any, Dict
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.stats import router as stats_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import bind_request_id, clear_request_id, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting LaunchBoard API",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )
    try:
        await init_db()
        # Recover any orphaned running collection runs from abnormal shutdown
        from app.core.database import async_session_factory
        from app.models.collection_run import CollectionRun
        from datetime import datetime, timezone
        from sqlalchemy import update
        async with async_session_factory() as session:
            await session.execute(
                update(CollectionRun)
                .where(CollectionRun.status == "running")
                .values(
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                    error_details=["Server restarted while run was in progress."],
                )
            )
            await session.commit()

        # Start the background refresh scheduler
        from app.services.scheduler import scheduler
        scheduler.start()
    except Exception as exc:
        logger.warning(
            "Database connection could not be established on startup; will retry on request",
            error=str(exc),
        )
    yield
    logger.info("Shutting down LaunchBoard API")
    from app.services.scheduler import scheduler
    await scheduler.stop()
    await close_db()


app = FastAPI(
    title="LaunchBoard API",
    description="AI-Powered Fresher Job & Internship Aggregator",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        bind_request_id(request_id)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        clear_request_id()
        return response


app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    return {
        "name": "LaunchBoard API",
        "description": "AI-Powered Fresher Job & Internship Aggregator",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "LaunchBoard API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
