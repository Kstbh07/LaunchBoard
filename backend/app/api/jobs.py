"""Jobs API router for LaunchBoard.

Provides endpoints for searching, filtering, paginating jobs,
retrieving individual job listings, and aggregating distinct roles and cities.
"""
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_session
from app.models.job import Job
from app.schemas.job import JobListResponse, JobResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Jobs"])

ALLOWED_SORT_FIELDS = {
    "collected_at": Job.collected_at,
    "posted_at": Job.posted_at,
    "company": Job.company,
    "title": Job.title,
    "classification_confidence": Job.classification_confidence,
}


class RoleCount(BaseModel):
    """Aggregated job count per distinct role category."""
    role_category: str = Field(..., description="Role category name")
    count: int = Field(..., description="Number of active job listings")

    model_config = ConfigDict(from_attributes=True)


class CityCount(BaseModel):
    """Aggregated job count per distinct normalized city."""
    city: str = Field(..., description="Normalized Indian city name")
    count: int = Field(..., description="Number of active job listings")

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Search and filter job listings",
    description=(
        "Query and filter active fresher & internship jobs with full-text search, "
        "faceted filters (role, city, employment type, experience level, remote), "
        "configurable sorting, and pagination."
    ),
    responses={
        200: {"description": "List of matching job listings with pagination metadata."},
        400: {"description": "Invalid query parameters (e.g. invalid sort column or order)."},
    },
)
@router.get("/api/jobs", response_model=JobListResponse, include_in_schema=False)
async def list_jobs(
    q: Optional[str] = Query(
        None,
        description="Search text matched against title, company, and description (case-insensitive)",
    ),
    role_category: Optional[str] = Query(
        None,
        description="Filter by role category (e.g., 'Backend Development', 'AI/ML Engineering')",
    ),
    city: Optional[str] = Query(
        None,
        description="Filter by normalized city name (e.g., 'Bengaluru', 'Pune')",
    ),
    employment_type: Optional[str] = Query(
        None,
        description="Filter by employment type (e.g., 'Internship', 'Full-time')",
    ),
    experience_level: Optional[str] = Query(
        None,
        description="Filter by experience level (e.g., 'Fresher', 'Entry-level')",
    ),
    is_remote: Optional[bool] = Query(
        None,
        description="Filter by remote work availability (true for remote only)",
    ),
    status_filter: str = Query(
        "active",
        alias="status",
        description="Filter by listing status (default: 'active')",
    ),
    sort_by: str = Query(
        "posted_at",
        description="Field to sort by: 'posted_at', 'collected_at', 'company', 'title'",
    ),
    sort_order: str = Query(
        "desc",
        description="Sort direction: 'asc' or 'desc'",
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of jobs per page (max 100)",
    ),
    session: AsyncSession = Depends(get_session),
) -> JobListResponse:
    """Search and filter aggregated jobs using SQLAlchemy."""
    logger.info(
        "searching_jobs",
        q=q,
        role_category=role_category,
        city=city,
        employment_type=employment_type,
        experience_level=experience_level,
        is_remote=is_remote,
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    conditions = []

    # 1. Full-text search across title, company, description using ILIKE and or_
    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                Job.title.ilike(search_pattern),
                Job.company.ilike(search_pattern),
                Job.description.ilike(search_pattern),
            )
        )

    # 2. Exact match faceted filters
    if role_category and role_category.strip():
        conditions.append(Job.role_category == role_category.strip())

    if city and city.strip():
        conditions.append(Job.city == city.strip())

    if employment_type and employment_type.strip():
        conditions.append(Job.employment_type == employment_type.strip())

    if experience_level and experience_level.strip():
        conditions.append(Job.experience_level == experience_level.strip())

    if is_remote is not None:
        conditions.append(Job.is_remote.is_(is_remote))

    if status_filter and status_filter.lower() != "all":
        conditions.append(Job.status == status_filter)

    # 3. Validate sorting parameters
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Allowed: {list(ALLOWED_SORT_FIELDS.keys())}",
        )

    sort_col = ALLOWED_SORT_FIELDS[sort_by]
    if sort_order.lower() == "asc":
        order_clause = sort_col.asc().nulls_last()
    elif sort_order.lower() == "desc":
        order_clause = sort_col.desc().nulls_last()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_order '{sort_order}'. Allowed: 'asc', 'desc'",
        )

    # 4. Total count query
    count_query = select(func.count(Job.id)).where(*conditions)
    count_result = await session.execute(count_query)
    total = count_result.scalar_one() or 0

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    # 5. Fetch paginated slice (with deterministic secondary tie-breaker to prevent pagination overlap)
    data_query = (
        select(Job)
        .where(*conditions)
        .order_by(order_clause, Job.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await session.execute(data_query)
    jobs = list(data_result.scalars().all())

    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get single job by UUID",
    description="Retrieve the complete details of a specific job listing by its unique UUID identifier.",
    responses={
        200: {"description": "Full job details."},
        404: {"description": "Job with specified ID not found."},
    },
)
@router.get("/api/jobs/{job_id}", response_model=JobResponse, include_in_schema=False)
async def get_job_by_id(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Retrieve an individual job listing by UUID."""
    logger.info("fetching_job_by_id", job_id=str(job_id))
    query = select(Job).where(Job.id == job_id)
    result = await session.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning("job_not_found", job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    return JobResponse.model_validate(job)


@router.get(
    "/roles",
    response_model=list[RoleCount],
    summary="Get distinct role categories",
    description="Retrieve all distinct role categories along with the count of active listings in each category.",
    responses={
        200: {"description": "List of role categories and active job counts."},
    },
)
@router.get("/api/roles", response_model=list[RoleCount], include_in_schema=False)
async def get_roles(
    session: AsyncSession = Depends(get_session),
) -> list[RoleCount]:
    """Return all distinct role categories with listing counts."""
    logger.info("fetching_roles_summary")
    query = (
        select(Job.role_category, func.count(Job.id).label("count"))
        .where(
            Job.role_category.isnot(None),
            Job.role_category != "",
            Job.status == "active",
        )
        .group_by(Job.role_category)
        .order_by(func.count(Job.id).desc())
    )
    result = await session.execute(query)
    rows = result.all()

    return [RoleCount(role_category=row[0], count=row[1]) for row in rows]


@router.get(
    "/cities",
    response_model=list[CityCount],
    summary="Get distinct cities",
    description="Retrieve all distinct normalized Indian cities along with the count of active listings in each city.",
    responses={
        200: {"description": "List of cities and active job counts."},
    },
)
@router.get("/api/cities", response_model=list[CityCount], include_in_schema=False)
async def get_cities(
    session: AsyncSession = Depends(get_session),
) -> list[CityCount]:
    """Return all distinct cities with active listing counts."""
    logger.info("fetching_cities_summary")
    query = (
        select(Job.city, func.count(Job.id).label("count"))
        .where(
            Job.city.isnot(None),
            Job.city != "",
            func.lower(Job.city) != "unknown",
            Job.status == "active",
        )
        .group_by(Job.city)
        .order_by(func.count(Job.id).desc())
    )
    result = await session.execute(query)
    rows = result.all()

    return [CityCount(city=row[0], count=row[1]) for row in rows]
