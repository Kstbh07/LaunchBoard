"""Admin API router for LaunchBoard.

Provides protected endpoints for triggering manual data collection refreshes,
checking pipeline telemetry, viewing dashboard metrics and LLM costs,
and exporting classification evaluation datasets as CSV.
"""
import csv
from datetime import datetime, timezone
import io
from typing import Any, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_session, verify_admin_key
from app.core.database import async_session_factory
from app.models.classification_usage import ClassificationUsage
from app.models.collection_run import CollectionRun
from app.models.job import Job
from app.models.source_status import SourceStatus
from app.schemas.admin import RefreshRequest, RefreshResponse, RefreshStatus
from app.schemas.stats import AdminDashboard, CostReport
from app.services.cost_tracker import PRICING_CONFIG

logger = structlog.get_logger(__name__)

router = APIRouter(
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
)


async def run_collection_pipeline_task(
    run_id: UUID,
    sources: Optional[list[str]] = None,
) -> None:
    """Execute the data collection and classification pipeline as a background task."""
    logger.info("starting_background_pipeline", run_id=str(run_id), sources=sources)
    try:
        from app.services.pipeline import CollectionPipeline

        async with async_session_factory() as session:
            pipeline = CollectionPipeline(
                db=session,
                trigger_type="manual",
                sources=sources,
                run_id=run_id,
            )
            await pipeline.run()
        logger.info("background_pipeline_succeeded", run_id=str(run_id))
    except Exception as exc:
        logger.error(
            "background_pipeline_failed",
            run_id=str(run_id),
            error=str(exc),
            exc_info=True,
        )


@router.post(
    "/admin/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual job collection refresh",
    description=(
        "Initiates the job aggregation, deduplication, and AI classification pipeline "
        "in the background. Fails if another collection run is currently in progress."
    ),
    responses={
        202: {"description": "Refresh run initiated successfully in the background."},
        403: {"description": "Missing or invalid admin API key."},
        409: {"description": "Another collection run is currently in progress."},
    },
)
@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
@router.post("/api/admin/refresh", response_model=RefreshResponse, status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    payload: Optional[RefreshRequest] = None,
    session: AsyncSession = Depends(get_session),
) -> RefreshResponse:
    """Trigger a manual collection and classification run."""
    logger.info("evaluating_refresh_trigger_request")

    # 1. Verify no existing run is active (recovering stale runs older than 15 minutes)
    now = datetime.now(timezone.utc)
    active_query = select(CollectionRun).where(CollectionRun.status == "running").limit(1)
    active_result = await session.execute(active_query)
    active_run = active_result.scalar_one_or_none()

    if active_run:
        started = active_run.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - started).total_seconds()
        if elapsed_seconds > 900:  # 15 minutes timeout for stale runs
            logger.warning(
                "recovering_stale_collection_run",
                active_run_id=str(active_run.id),
                elapsed_seconds=elapsed_seconds,
            )
            active_run.status = "failed"
            active_run.completed_at = now
            active_run.error_details = ["Execution timed out or server restarted while running."]
            await session.commit()
        else:
            logger.warning("collection_run_conflict", active_run_id=str(active_run.id))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A collection run is already in progress (Run ID: {active_run.id})",
            )

    # 2. Create the CollectionRun record in running state
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    new_run = CollectionRun(
        id=run_id,
        started_at=now,
        status="running",
        trigger_type="manual",
        total_fetched=0,
        total_new=0,
        total_updated=0,
        total_duplicates=0,
        total_classified=0,
        total_failed=0,
        total_errors=0,
        error_details=[],
        source_results={},
    )
    session.add(new_run)
    await session.commit()

    # 3. Queue pipeline in background
    sources = payload.sources if payload and payload.sources else None
    background_tasks.add_task(run_collection_pipeline_task, run_id=run_id, sources=sources)

    logger.info("collection_run_dispatched", run_id=str(run_id), sources=sources)
    return RefreshResponse(
        run_id=run_id,
        status="running",
        message="Manual collection pipeline successfully queued in background.",
    )


@router.post(
    "/admin/classify/backlog",
    summary="Process unclassified job backlog",
    description="Progressively classifies pending and failed job records using rate-limit-compliant pacing.",
)
@router.post("/classify/backlog", include_in_schema=False)
@router.post("/api/admin/classify/backlog", include_in_schema=False)
async def process_classification_backlog_endpoint(
    background_tasks: BackgroundTasks,
    limit: int = 30,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Trigger background backlog processing for pending/failed jobs."""
    logger.info("queuing_classification_backlog", limit=limit)

    async def _backlog_task(batch_limit: int):
        from app.services.classification_backlog import ClassificationBacklogService
        try:
            async with async_session_factory() as task_session:
                service = ClassificationBacklogService(db=task_session)
                res = await service.process_batch(limit=batch_limit)
                logger.info("backlog_batch_completed", **res)
        except Exception as exc:
            logger.error("backlog_batch_failed", error=str(exc))

    background_tasks.add_task(_backlog_task, limit)
    return {
        "status": "accepted",
        "message": f"Classification backlog processing queued for up to {limit} jobs in the background.",
    }


@router.get(
    "/admin/refresh/status",
    response_model=RefreshStatus,
    summary="Get latest refresh status",
    description="Returns the execution status, metrics, and source breakdown for the most recent collection run.",
    responses={
        200: {"description": "Details of the most recent collection run."},
        403: {"description": "Missing or invalid admin API key."},
        404: {"description": "No collection runs have been executed yet."},
    },
)
@router.get("/refresh/status", response_model=RefreshStatus, include_in_schema=False)
@router.get("/api/admin/refresh/status", response_model=RefreshStatus, include_in_schema=False)
async def get_refresh_status(
    session: AsyncSession = Depends(get_session),
) -> RefreshStatus:
    """Retrieve telemetry for the latest collection run."""
    logger.info("fetching_latest_refresh_status")
    query = select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(1)
    result = await session.execute(query)
    latest_run = result.scalar_one_or_none()

    if not latest_run:
        logger.warning("no_collection_runs_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collection runs found",
        )

    duration = None
    if latest_run.completed_at and latest_run.started_at:
        duration = round((latest_run.completed_at - latest_run.started_at).total_seconds(), 2)

    return RefreshStatus(
        run_id=latest_run.id,
        status=latest_run.status,
        started_at=latest_run.started_at,
        completed_at=latest_run.completed_at,
        total_fetched=latest_run.total_fetched,
        total_new=latest_run.total_new,
        total_updated=latest_run.total_updated,
        total_duplicates=latest_run.total_duplicates,
        total_classified=latest_run.total_classified,
        total_failed=latest_run.total_failed,
        total_errors=latest_run.total_errors,
        error_details=latest_run.error_details or [],
        source_results=latest_run.source_results or {},
        duration_seconds=duration,
    )


@router.get(
    "/admin/dashboard",
    response_model=AdminDashboard,
    summary="Get admin dashboard overview data",
    description="Consolidates aggregated job counts, scraper source health, AI classification costs, and recent run history.",
    responses={
        200: {"description": "Aggregated administration metrics and telemetry."},
        403: {"description": "Missing or invalid admin API key."},
    },
)
@router.get("/dashboard", response_model=AdminDashboard, include_in_schema=False)
@router.get("/api/admin/dashboard", response_model=AdminDashboard, include_in_schema=False)
async def get_admin_dashboard(
    session: AsyncSession = Depends(get_session),
) -> AdminDashboard:
    """Compile and return comprehensive administration and telemetry metrics."""
    logger.info("compiling_admin_dashboard_metrics")

    # 1. Total jobs collected
    total_jobs_res = await session.execute(select(func.count(Job.id)))
    total_jobs_collected = total_jobs_res.scalar_one() or 0

    # 2. Unique jobs by fingerprint
    unique_jobs_res = await session.execute(
        select(func.count(func.distinct(Job.fingerprint))).where(Job.fingerprint.isnot(None))
    )
    unique_jobs = unique_jobs_res.scalar_one() or 0
    if unique_jobs == 0 and total_jobs_collected > 0:
        unique_jobs = total_jobs_collected

    # 3. Duplicate jobs detected
    duplicate_jobs_detected = max(0, total_jobs_collected - unique_jobs)

    # 4. Jobs classified
    classified_res = await session.execute(
        select(func.count(Job.id)).where(Job.classification_status == "classified")
    )
    jobs_classified = classified_res.scalar_one() or 0

    # 5. Failed classifications
    failed_res = await session.execute(
        select(func.count(Job.id)).where(Job.classification_status == "failed")
    )
    failed_classifications = failed_res.scalar_one() or 0

    # 6. Source-wise stats
    sources_res = await session.execute(
        select(SourceStatus).order_by(SourceStatus.source_name.asc())
    )
    source_rows = sources_res.scalars().all()
    source_stats = [
        {
            "id": str(s.id),
            "source_name": s.source_name,
            "is_enabled": s.is_enabled,
            "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
            "last_failure_at": s.last_failure_at.isoformat() if s.last_failure_at else None,
            "last_error_message": s.last_error_message,
            "total_jobs_collected": s.total_jobs_collected,
            "total_runs": s.total_runs,
            "total_failures": s.total_failures,
            "consecutive_failures": s.consecutive_failures,
            "config": s.config or {},
        }
        for s in source_rows
    ]

    # 7. LLM cost report from classification_usage
    usage_res = await session.execute(
        select(
            func.coalesce(func.sum(ClassificationUsage.total_input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ClassificationUsage.total_output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(ClassificationUsage.total_requests), 0).label("requests"),
            func.coalesce(func.sum(ClassificationUsage.total_cost_usd), 0.0).label("cost_usd"),
            func.max(ClassificationUsage.recorded_at).label("last_updated"),
        )
    )
    usage_row = usage_res.one()
    tot_input = int(usage_row.input_tokens)
    tot_output = int(usage_row.output_tokens)
    tot_requests = int(usage_row.requests)
    tot_cost_usd = round(float(usage_row.cost_usd), 4)
    last_updated = usage_row.last_updated

    avg_cost = round(tot_cost_usd / tot_requests, 6) if tot_requests > 0 else 0.0
    cost_per_1000 = round(avg_cost * 1000.0, 4)

    pricing = PRICING_CONFIG.get("gemini-2.0-flash", {})

    cost_report = CostReport(
        total_input_tokens=tot_input,
        total_output_tokens=tot_output,
        total_tokens=tot_input + tot_output,
        total_requests=tot_requests,
        total_cost_usd=tot_cost_usd,
        avg_cost_per_job=avg_cost,
        cost_per_1000_jobs=cost_per_1000,
        model_name="gemini-2.0-flash",
        pricing_config=pricing,
        last_updated=last_updated,
        note="Costs are estimates based on published API pricing.",
    )

    # 8. Collection history (last 10 runs) & last_collection_run
    runs_res = await session.execute(
        select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(10)
    )
    run_rows = runs_res.scalars().all()

    def format_collection_run(r: CollectionRun) -> dict[str, Any]:
        duration = None
        if r.completed_at and r.started_at:
            c = r.completed_at.replace(tzinfo=None) if r.completed_at.tzinfo else r.completed_at
            s = r.started_at.replace(tzinfo=None) if r.started_at.tzinfo else r.started_at
            duration = round((c - s).total_seconds(), 2)

        return {
            "id": str(r.id),
            "run_id": str(r.id),
            "status": r.status,
            "trigger_type": r.trigger_type,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_seconds": duration,
            "total_fetched": r.total_fetched,
            "total_new": r.total_new,
            "total_updated": r.total_updated,
            "total_duplicates": r.total_duplicates,
            "total_classified": r.total_classified,
            "total_failed": r.total_failed,
            "total_errors": r.total_errors,
            "error_details": r.error_details or [],
            "source_results": r.source_results or {},
        }

    collection_history = [format_collection_run(r) for r in run_rows]
    last_collection_run = collection_history[0] if collection_history else None

    # Scheduler status
    try:
        from app.services.scheduler import scheduler
        sched_status = scheduler.get_status()
    except Exception:
        sched_status = None

    # Documented restricted platforms
    restricted_sources = [
        {
            "name": "Internshala",
            "type": "Indian Internship Platform",
            "status": "restricted",
            "reason": "Robots.txt disallows automated scrapers; requires official university/enterprise partner API.",
            "recommendation": "Apply for Internshala Partner / College Placement API access.",
        },
        {
            "name": "Naukri",
            "type": "Indian Job Portal",
            "status": "restricted",
            "reason": "Enforces strict Cloudflare/ShieldSquare anti-bot challenges; automated scraping violates Terms of Service.",
            "recommendation": "Use Naukri Enterprise Recruiter API or RSS feeds where permitted.",
        },
        {
            "name": "Wellfound (AngelList)",
            "type": "Startup Job Board",
            "status": "restricted",
            "reason": "Cloudflare Turnstile gates programmatically block scrapers without human browser verification.",
            "recommendation": "Use Ashby / Greenhouse integrations of individual YC & Wellfound startups directly.",
        },
        {
            "name": "Cutshort",
            "type": "Indian Tech Recruitment",
            "status": "restricted",
            "reason": "Requires authenticated login session cookies; scraping candidate feeds is prohibited.",
            "recommendation": "Subscribe to Cutshort employer webhook feeds.",
        },
        {
            "name": "Apna & Freshersworld",
            "type": "Indian Entry-Level Job Boards",
            "status": "restricted",
            "reason": "Require mobile OTP / session-based authentication to view full application details.",
            "recommendation": "Use verified public boards (Greenhouse, Lever, Himalayas, Jobicy, RemoteOK).",
        },
        {
            "name": "LinkedIn & Indeed",
            "type": "Global Job Aggregators",
            "status": "restricted",
            "reason": "User agreements strictly prohibit automated extraction; Indeed deprecated public RSS search feeds.",
            "recommendation": "Direct company career board integrations (Greenhouse, Lever, Ashby, Workable).",
        },
    ]

    return AdminDashboard(
        total_jobs_collected=total_jobs_collected,
        unique_jobs=unique_jobs,
        duplicate_jobs_detected=duplicate_jobs_detected,
        jobs_classified=jobs_classified,
        failed_classifications=failed_classifications,
        source_stats=source_stats,
        restricted_sources=restricted_sources,
        scheduler_status=sched_status,
        cost_report=cost_report,
        last_collection_run=last_collection_run,
        collection_history=collection_history,
    )


@router.get(
    "/admin/evaluation/export",
    summary="Export CSV for evaluation",
    description=(
        "Exports up to 50 AI-classified job listings into CSV format with "
        "model classification columns and empty evaluation fields for benchmarking accuracy."
    ),
    responses={
        200: {
            "description": "Evaluation dataset in CSV format.",
            "content": {"text/csv": {}},
        },
        403: {"description": "Missing or invalid admin API key."},
    },
)
@router.get("/evaluation/export", include_in_schema=False)
@router.get("/api/admin/evaluation/export", include_in_schema=False)
async def export_evaluation_csv(
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Generate and stream a 50-job evaluation CSV dataset."""
    logger.info("generating_job_evaluation_csv_export")

    query = (
        select(Job)
        .where(Job.classification_status == "classified")
        .order_by(Job.collected_at.desc())
        .limit(50)
    )
    result = await session.execute(query)
    jobs = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)

    # Required CSV header
    writer.writerow([
        "job_id",
        "title",
        "company",
        "description",
        "ai_role_category",
        "ai_city",
        "ai_confidence",
        "ai_skills",
        "manual_role",
        "manual_city",
        "role_correct",
        "city_correct",
        "both_correct",
    ])

    for job in jobs:
        desc_snippet = (
            (job.description or "")[:500]
            .replace("\r\n", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .strip()
        )
        skills_formatted = (
            ", ".join(str(s) for s in job.skills)
            if isinstance(job.skills, list)
            else str(job.skills or "")
        )
        confidence_str = (
            f"{job.classification_confidence:.2f}"
            if job.classification_confidence is not None
            else ""
        )
        writer.writerow([
            str(job.id),
            job.title or "",
            job.company or "",
            desc_snippet,
            job.role_category or "",
            job.city or "",
            confidence_str,
            skills_formatted,
            "",  # manual_role (empty for human annotation)
            "",  # manual_city (empty for human annotation)
            "",  # role_correct (empty for human annotation)
            "",  # city_correct (empty for human annotation)
            "",  # both_correct (empty for human annotation)
        ])

    csv_content = output.getvalue()
    output.close()

    logger.info("job_evaluation_csv_generated", job_count=len(jobs))

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="job_evaluation_export.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
