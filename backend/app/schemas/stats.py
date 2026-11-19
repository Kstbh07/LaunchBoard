from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    total_active_jobs: int
    total_unique_jobs: int
    total_companies: int
    total_cities: int
    total_remote_jobs: int
    total_internships: int = 0
    total_fresher_jobs: int = 0
    jobs_by_role: dict[str, int]
    jobs_by_city: dict[str, int]
    jobs_by_employment_type: dict[str, int]
    jobs_by_experience_level: dict[str, int]
    last_successful_refresh: Optional[datetime] = None
    total_sources: int


class CostReport(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_requests: int
    total_cost_usd: float
    avg_cost_per_job: float
    cost_per_1000_jobs: float
    model_name: str
    pricing_config: dict[str, Any]
    last_updated: Optional[datetime] = None
    note: str = "Costs are estimates based on published API pricing."


class AdminDashboard(BaseModel):
    total_jobs_collected: int
    unique_jobs: int
    duplicate_jobs_detected: int
    jobs_classified: int
    failed_classifications: int
    source_stats: list[dict[str, Any]] = Field(default_factory=list)
    restricted_sources: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_status: Optional[dict[str, Any]] = None
    cost_report: CostReport
    last_collection_run: Optional[dict[str, Any]] = None
    collection_history: list[dict[str, Any]] = Field(default_factory=list)
