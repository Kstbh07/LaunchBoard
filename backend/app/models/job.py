from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
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
    from app.models.classification import Classification
    from app.models.job_source import JobSource


class Job(Base):
    """Job entity representing aggregated fresher and entry-level positions."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # Internship, Full-time, Part-time, Contract
    experience_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # Fresher, Internship, Entry-level, Experienced, Unknown
    application_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )  # active, expired, removed
    role_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    skills: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )  # SHA256 dedup fingerprint
    city: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )  # normalized city
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    classification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )  # pending, classified, failed, review

    # Relationships
    sources: Mapped[list[JobSource]] = relationship(
        "JobSource",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    classifications: Mapped[list[Classification]] = relationship(
        "Classification",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_company_title_location", "company", "title", "location"),
        Index("ix_jobs_status_role_category", "status", "role_category"),
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, title='{self.title}', company='{self.company}', "
            f"status='{self.status}', fingerprint='{self.fingerprint}')>"
        )
