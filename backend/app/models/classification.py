from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


class Classification(Base):
    """LLM classification results and execution telemetry for a job listing."""

    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    skills: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_remote: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # full LLM response payload
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        server_default="success",
    )  # success, failed, retry

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="classifications")

    def __repr__(self) -> str:
        return (
            f"<Classification(id={self.id}, job_id={self.job_id}, "
            f"model_name='{self.model_name}', status='{self.status}', "
            f"confidence={self.confidence})>"
        )
