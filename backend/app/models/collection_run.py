from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.classification_usage import ClassificationUsage


class CollectionRun(Base):
    """Execution telemetry and tracking for scheduled or manual job aggregation runs."""

    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        server_default="running",
    )  # running, completed, failed, partial
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # scheduled, manual
    total_fetched: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_new: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_duplicates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_classified: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_errors: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_details: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    source_results: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )  # per-source breakdown

    # Relationships
    classification_usages: Mapped[list[ClassificationUsage]] = relationship(
        "ClassificationUsage",
        back_populates="collection_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CollectionRun(id={self.id}, status='{self.status}', "
            f"trigger_type='{self.trigger_type}', total_fetched={self.total_fetched}, "
            f"total_new={self.total_new})>"
        )
