"""API Dependencies."""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings

api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an asynchronous database session."""
    async for session in get_db():
        yield session


async def verify_admin_key(api_key: str = Security(api_key_header)) -> str:
    """Dependency verifying admin API key in the X-Admin-API-Key header."""
    settings = get_settings()
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key"
        )
    return api_key
