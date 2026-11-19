from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobBase(BaseModel):
    title: str
    company: str
    description: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    application_url: str
    source_name: str
    source_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    is_remote: bool = False


class JobCreate(JobBase):
    source_job_id: Optional[str] = None
    fingerprint: Optional[str] = None


class JobResponse(BaseModel):
    id: UUID
    title: str
    company: str
    description: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    application_url: str
    source_name: str
    source_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    collected_at: datetime
    last_verified_at: datetime
    status: str
    role_category: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    is_remote: bool
    city: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_status: str

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobSearchParams(BaseModel):
    q: Optional[str] = None  # search query
    role_category: Optional[str] = None
    city: Optional[str] = None
    employment_type: Optional[str] = None
    is_remote: Optional[bool] = None
    experience_level: Optional[str] = None
    status: str = "active"
    sort_by: str = "collected_at"  # collected_at, posted_at, company, title
    sort_order: str = "desc"  # asc, desc
    page: int = 1
    page_size: int = 20
