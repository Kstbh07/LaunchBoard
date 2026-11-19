from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    logger.info("Initializing database connection...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successfully established.")
    except Exception as exc:
        logger.error("Failed to connect to database", error=str(exc))
        raise


async def close_db() -> None:
    logger.info("Disposing database connection pool...")
    await engine.dispose()
    logger.info("Database connection pool disposed.")
