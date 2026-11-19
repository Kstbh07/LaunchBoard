"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
import json
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """LaunchBoard backend configuration settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/launchboard",
        description="PostgreSQL async connection string (asyncpg)",
    )

    # AI Service Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key for AI job classification",
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key (alternative provider)",
    )
    AI_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Model identifier for job extraction and classification",
    )
    AI_PROVIDER: str = Field(
        default="gemini",
        description="Default AI provider: 'gemini' or 'openai'",
    )

    # Security & Administration
    ADMIN_API_KEY: str = Field(
        default="dev-admin-key",
        description="Secret key to protect admin and collector triggers",
    )

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://launchboard.vercel.app"],
        description="Allowed CORS origin URLs",
    )

    # Job Collection Parameters
    COLLECTION_BATCH_SIZE: int = Field(
        default=50,
        description="Batch size for concurrent job scrapers and ingestion",
    )

    # AI Classification Confidence Thresholds
    CLASSIFICATION_CONFIDENCE_HIGH: float = Field(
        default=0.85,
        description="High confidence threshold for auto-publishing",
    )
    CLASSIFICATION_CONFIDENCE_MEDIUM: float = Field(
        default=0.65,
        description="Medium confidence threshold for manual review queue",
    )

    # External Job Board APIs
    ADZUNA_APP_ID: Optional[str] = Field(
        default=None,
        description="Adzuna developer application ID",
    )
    ADZUNA_APP_KEY: Optional[str] = Field(
        default=None,
        description="Adzuna developer application key",
    )
    FINDWORK_API_KEY: Optional[str] = Field(
        default=None,
        description="Findwork job API key",
    )

    # Application Environment & Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment: development, staging, production",
    )
    ENABLE_SCHEDULER: bool = Field(
        default=True,
        description="Enable automatic background collection scheduler",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, value: str) -> str:
        """Normalize database connection string for asyncpg and Render PostgreSQL."""
        if not value or not isinstance(value, str):
            return value
        val = value.strip().strip("'\"")
        # Render and some cloud providers supply postgres:// instead of postgresql://
        if val.startswith("postgres://"):
            val = "postgresql+asyncpg://" + val[len("postgres://"):]
        elif val.startswith("postgresql://") and not val.startswith("postgresql+asyncpg://"):
            val = "postgresql+asyncpg://" + val[len("postgresql://"):]

        # asyncpg does not accept sslmode query parameter (requires ssl)
        try:
            u = make_url(val)
            query = dict(u.query)
            if "sslmode" in query:
                ssl_val = query.pop("sslmode")
                if "ssl" not in query:
                    query["ssl"] = ssl_val
                u = u._replace(query=query)
                val = u.render_as_string(hide_password=False)
        except Exception:
            pass

        return val

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Parse string representation of CORS origins (JSON or comma-separated)."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        elif isinstance(value, (list, tuple, set)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return []


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
