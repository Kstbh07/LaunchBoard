from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Raw job as collected from a source before dedup/classification
class RawJob(BaseModel):
    title: str
    company: str
    description: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    application_url: str
    source_name: str
    source_url: Optional[str] = None
    source_job_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    is_remote: bool = False
    skills: list[str] = Field(default_factory=list)

    @field_validator("application_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("application_url must be a valid HTTP URL")
        return v

    @field_validator("title", "company")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
