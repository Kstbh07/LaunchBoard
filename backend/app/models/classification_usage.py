from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
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
    from app.models.collection_run import CollectionRun


class ClassificationUsage(Base):
    """Aggregate token usage and estimated cost tracking for AI classification."""

    __tablename__ = "classification_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    collection_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("collection_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )  # estimated cost in USD
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    pricing_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )  # pricing rates used for calculation

    # Relationships
    collection_run: Mapped[Optional[CollectionRun]] = relationship(
        "CollectionRun",
        back_populates="classification_usages",
    )

    def __repr__(self) -> str:
        return (
            f"<ClassificationUsage(id={self.id}, model_name='{self.model_name}', "
            f"requests={self.total_requests}, cost_usd={self.total_cost_usd})>"
        )
