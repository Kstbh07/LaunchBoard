from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


class JobSource(Base):
    """Source provenance tracking for aggregated job listings."""

    __tablename__ = "job_sources"

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
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    source_job_id: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )  # original identifier from the source
    application_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="sources")

    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_job_id",
            name="uq_job_sources_source_name_source_job_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<JobSource(id={self.id}, job_id={self.job_id}, "
            f"source_name='{self.source_name}', source_job_id='{self.source_job_id}', "
            f"is_primary={self.is_primary})>"
        )
