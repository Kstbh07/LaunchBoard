"""Dashboard statistics API router for LaunchBoard."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_session
from app.models.collection_run import CollectionRun
from app.models.job import Job
from app.models.source_status import SourceStatus
from app.schemas.stats import StatsResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Stats"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get aggregated dashboard statistics",
    description=(
        "Returns comprehensive real-time statistics including total active jobs, "
        "unique deduplicated jobs, distinct companies, remote jobs, top cities, "
        "and breakdowns by role category, employment type, and experience level."
    ),
    responses={
        200: {"description": "Real-time aggregated platform statistics."},
    },
)
@router.get("/api/stats", response_model=StatsResponse, include_in_schema=False)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    """Calculate and return platform-wide statistics from the database."""
    logger.info("generating_platform_statistics")

    # 1. Total active jobs
    total_active_res = await session.execute(
        select(func.count(Job.id)).where(Job.status == "active")
    )
    total_active_jobs = total_active_res.scalar_one() or 0

    # 2. Total unique jobs (distinct fingerprints)
    total_unique_res = await session.execute(
        select(func.count(func.distinct(Job.fingerprint))).where(Job.fingerprint.isnot(None))
    )
    total_unique_jobs = total_unique_res.scalar_one() or 0
    if total_unique_jobs == 0 and total_active_jobs > 0:
        total_unique_jobs = total_active_jobs

    # 3. Total distinct companies (active jobs)
    companies_res = await session.execute(
        select(func.count(func.distinct(Job.company))).where(
            Job.company.isnot(None),
            Job.company != "",
            Job.status == "active",
        )
    )
    total_companies = companies_res.scalar_one() or 0

    # 4. Total distinct cities (active jobs, excluding Unknown)
    cities_count_res = await session.execute(
        select(func.count(func.distinct(Job.city))).where(
            Job.city.isnot(None),
            Job.city != "",
            func.lower(Job.city) != "unknown",
            Job.status == "active",
        )
    )
    total_cities = cities_count_res.scalar_one() or 0

    # 5. Total remote jobs
    remote_res = await session.execute(
        select(func.count(Job.id)).where(
            Job.is_remote.is_(True),
            Job.status == "active",
        )
    )
    total_remote_jobs = remote_res.scalar_one() or 0

    # 5a. Total internships
    internship_res = await session.execute(
        select(func.count(Job.id)).where(
            Job.status == "active",
            or_(
                func.lower(Job.employment_type) == "internship",
                func.lower(Job.experience_level) == "internship",
                Job.title.ilike("%intern%"),
            ),
        )
    )
    total_internships = internship_res.scalar_one() or 0

    # 5b. Total fresher jobs
    fresher_res = await session.execute(
        select(func.count(Job.id)).where(
            Job.status == "active",
            or_(
                func.lower(Job.experience_level).in_(["fresher", "entry-level"]),
                Job.title.ilike("%fresher%"),
                Job.title.ilike("%trainee%"),
                Job.title.ilike("%graduate%"),
            ),
        )
    )
    total_fresher_jobs = fresher_res.scalar_one() or 0

    # 6. Jobs by role category
    roles_res = await session.execute(
        select(Job.role_category, func.count(Job.id))
        .where(
            Job.role_category.isnot(None),
            Job.role_category != "",
            Job.status == "active",
        )
        .group_by(Job.role_category)
        .order_by(func.count(Job.id).desc())
    )
    jobs_by_role = {row[0]: row[1] for row in roles_res.all()}

    # 7. Jobs by city (top 20)
    cities_res = await session.execute(
        select(Job.city, func.count(Job.id))
        .where(
            Job.city.isnot(None),
            Job.city != "",
            func.lower(Job.city) != "unknown",
            Job.status == "active",
        )
        .group_by(Job.city)
        .order_by(func.count(Job.id).desc())
        .limit(20)
    )
    jobs_by_city = {row[0]: row[1] for row in cities_res.all()}

    # 8. Jobs by employment type
    emp_res = await session.execute(
        select(Job.employment_type, func.count(Job.id))
        .where(
            Job.employment_type.isnot(None),
            Job.employment_type != "",
            Job.status == "active",
        )
        .group_by(Job.employment_type)
        .order_by(func.count(Job.id).desc())
    )
    jobs_by_employment_type = {row[0]: row[1] for row in emp_res.all()}

    # 9. Jobs by experience level
    exp_res = await session.execute(
        select(Job.experience_level, func.count(Job.id))
        .where(
            Job.experience_level.isnot(None),
            Job.experience_level != "",
            Job.status == "active",
        )
        .group_by(Job.experience_level)
        .order_by(func.count(Job.id).desc())
    )
    jobs_by_experience_level = {row[0]: row[1] for row in exp_res.all()}

    # 10. Last successful refresh from collection_runs
    refresh_stmt = (
        select(CollectionRun.completed_at)
        .where(CollectionRun.status.in_(["completed", "success"]))
        .order_by(CollectionRun.completed_at.desc())
        .limit(1)
    )
    refresh_res = await session.execute(refresh_stmt)
    last_successful_refresh = refresh_res.scalar_one_or_none()

    # 11. Total active scraping sources from source_status
    try:
        sources_res = await session.execute(
            select(func.count(SourceStatus.id)).where(SourceStatus.is_enabled.is_(True))
        )
        total_sources = sources_res.scalar_one() or 0
        if total_sources == 0:
            sources_res2 = await session.execute(select(func.count(SourceStatus.id)))
            total_sources = sources_res2.scalar_one() or 0
    except Exception:
        total_sources = 0

    if total_sources == 0:
        fallback_res = await session.execute(
            select(func.count(func.distinct(Job.source_name))).where(
                Job.source_name.isnot(None),
                Job.source_name != "",
            )
        )
        total_sources = fallback_res.scalar_one() or 0

    logger.info(
        "platform_statistics_computed",
        active_jobs=total_active_jobs,
        unique_jobs=total_unique_jobs,
        companies=total_companies,
        cities=total_cities,
        remote_jobs=total_remote_jobs,
        sources=total_sources,
    )

    return StatsResponse(
        total_active_jobs=total_active_jobs,
        total_unique_jobs=total_unique_jobs,
        total_companies=total_companies,
        total_cities=total_cities,
        total_remote_jobs=total_remote_jobs,
        total_internships=total_internships,
        total_fresher_jobs=total_fresher_jobs,
        jobs_by_role=jobs_by_role,
        jobs_by_city=jobs_by_city,
        jobs_by_employment_type=jobs_by_employment_type,
        jobs_by_experience_level=jobs_by_experience_level,
        last_successful_refresh=last_successful_refresh,
        total_sources=total_sources,
    )
