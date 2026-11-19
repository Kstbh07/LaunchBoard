from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    sources: Optional[list[str]] = None  # specific sources, or all if None


class RefreshResponse(BaseModel):
    run_id: UUID
    status: str
    message: str


class RefreshStatus(BaseModel):
    run_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_fetched: int
    total_new: int
    total_updated: int
    total_duplicates: int
    total_classified: int
    total_failed: int
    total_errors: int
    error_details: list[Any] = Field(default_factory=list)
    source_results: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: Optional[float] = None
