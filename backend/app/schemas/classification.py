from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# LLM Classification response schema — what we expect from Gemini
class ClassificationResult(BaseModel):
    role_category: str = Field(
        ...,
        description=(
            "One of: Software Development, Frontend Development, Backend Development, "
            "Full Stack Development, AI/ML Engineering, Data Science, Data Analytics, "
            "DevOps / Cloud, Cybersecurity, Mobile Development, QA / Testing, "
            "UI/UX Design, Product Management, Business Development, Other"
        ),
    )
    city: str = Field(default="Unknown", description="Normalized Indian city name or Unknown")
    skills: list[str] = Field(default_factory=list, description="Technical skills extracted")
    experience_level: str = Field(
        ...,
        description="One of: Fresher, Internship, Entry-level, Experienced, Unknown",
    )
    employment_type: str = Field(
        ...,
        description="One of: Internship, Full-time, Part-time, Contract",
    )
    is_remote: bool = Field(default=False)
    confidence: float = Field(..., ge=0.0, le=1.0)


# Classification record from DB
class ClassificationResponse(BaseModel):
    id: UUID
    job_id: UUID
    model_name: str
    role_category: Optional[str] = None
    city: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    is_remote: bool
    confidence: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    classified_at: datetime

    model_config = ConfigDict(from_attributes=True)
