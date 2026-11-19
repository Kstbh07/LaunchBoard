"""Classification Backlog Processing Service for LaunchBoard.

Enables resumable, rate-limit-compliant progressive classification of
pending and failed job records without blocking pipeline ingestion runs.
Strictly respects provider rate limits (e.g. 15 RPM for Gemini free-tier).
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.classification import Classification
from app.models.classification_usage import ClassificationUsage
from app.models.job import Job
from app.services.classifier import ClassificationService
from app.services.cost_tracker import CostTracker

logger = structlog.get_logger(__name__)

DEFAULT_RATE_LIMIT_DELAY = 4.2  # 14.28 RPM, cleanly under 15 RPM limit


class ClassificationBacklogService:
    """Processes backlog of unclassified jobs with pacing and resume support."""

    def __init__(
        self,
        db: AsyncSession,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    ) -> None:
        self.db = db
        self.rate_limit_delay = rate_limit_delay
        self.classifier = ClassificationService()
        self.cost_tracker = CostTracker(self.classifier.model_name)

    async def get_backlog_counts(self) -> dict[str, int]:
        """Return counts of classified, pending, and failed jobs."""
        classified_res = await self.db.execute(
            select(func.count(Job.id)).where(Job.classification_status == "classified")
        )
        pending_res = await self.db.execute(
            select(func.count(Job.id)).where(Job.classification_status == "pending")
        )
        failed_res = await self.db.execute(
            select(func.count(Job.id)).where(Job.classification_status == "failed")
        )
        total_res = await self.db.execute(select(func.count(Job.id)))

        return {
            "total_jobs": total_res.scalar_one() or 0,
            "classified": classified_res.scalar_one() or 0,
            "pending": pending_res.scalar_one() or 0,
            "failed": failed_res.scalar_one() or 0,
        }

    async def process_batch(
        self,
        limit: int = 30,
        retry_failed: bool = True,
    ) -> dict[str, Any]:
        """Process a batch of unclassified jobs with rate limiting and checkpointing.

        Args:
            limit: Maximum number of jobs to classify in this batch.
            retry_failed: Whether to include previously failed jobs in the batch.

        Returns:
            Dictionary with batch execution telemetry and token usage.
        """
        if not self.classifier.available:
            logger.warning("classifier_unavailable", reason="Gemini/OpenAI API key not configured")
            return {
                "status": "skipped",
                "reason": "Classifier API not configured",
                "processed": 0,
                "classified": 0,
                "failed": 0,
            }

        # Query eligible backlog jobs: pending, or optionally failed
        statuses = ["pending"]
        if retry_failed:
            statuses.append("failed")

        query = (
            select(Job)
            .where(
                Job.status == "active",
                Job.classification_status.in_(statuses),
            )
            .order_by(Job.collected_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        jobs = result.scalars().all()

        if not jobs:
            counts = await self.get_backlog_counts()
            return {
                "status": "completed",
                "message": "No pending jobs found in backlog",
                "processed": 0,
                "classified": 0,
                "failed": 0,
                "counts": counts,
            }

        logger.info(
            "starting_backlog_classification",
            batch_size=len(jobs),
            model=self.classifier.model_name,
            rate_limit_delay=self.rate_limit_delay,
        )

        classified_count = 0
        failed_count = 0
        processed_count = 0

        for idx, job in enumerate(jobs):
            processed_count += 1
            logger.info(
                "classifying_backlog_job",
                index=idx + 1,
                total=len(jobs),
                job_id=str(job.id)[:8],
                title=job.title[:40],
                company=job.company,
            )

            try:
                res, usage = await self.classifier.classify_job(
                    title=job.title,
                    company=job.company,
                    description=job.description,
                    location=job.location,
                )

                if res:
                    # Defensive slicing for PostgreSQL column safety
                    safe_role = res.role_category[:95] if res.role_category else None
                    safe_city = res.city[:195] if res.city else None
                    safe_exp = res.experience_level[:45] if res.experience_level else None
                    safe_emp = res.employment_type[:45] if res.employment_type else None

                    job.role_category = safe_role
                    job.city = safe_city
                    job.skills = res.skills
                    job.experience_level = safe_exp
                    job.employment_type = safe_emp
                    job.is_remote = res.is_remote
                    job.classification_confidence = res.confidence

                    conf_level = self.classifier.get_confidence_level(res.confidence)
                    job.classification_status = (
                        "classified"
                        if conf_level == "high"
                        else "review"
                        if conf_level == "medium"
                        else "uncertain"
                    )

                    # Persist detailed classification record
                    cls_record = Classification(
                        id=uuid4(),
                        job_id=job.id,
                        model_name=usage.get("model_name", self.classifier.model_name)[:95],
                        role_category=safe_role,
                        city=safe_city,
                        skills=res.skills,
                        experience_level=safe_exp,
                        employment_type=safe_emp,
                        is_remote=res.is_remote,
                        confidence=res.confidence,
                        raw_response=res.model_dump_json(),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        processing_time_ms=usage.get("processing_time_ms", 0),
                        status="success",
                    )
                    self.db.add(cls_record)

                    self.cost_tracker.record_usage(
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                    classified_count += 1
                else:
                    job.classification_status = "failed"
                    failed_count += 1

                    fail_record = Classification(
                        id=uuid4(),
                        job_id=job.id,
                        model_name=usage.get("model_name", self.classifier.model_name),
                        status="failed",
                        raw_response=usage.get("error", "Classification failed"),
                        processing_time_ms=usage.get("processing_time_ms", 0),
                    )
                    self.db.add(fail_record)

            except Exception as exc:
                logger.error(
                    "backlog_job_classification_exception",
                    job_id=str(job.id),
                    error=str(exc),
                )
                job.classification_status = "failed"
                failed_count += 1

            # Checkpoint: Commit immediately after each job so progress is never lost
            await self.db.commit()

            # Pacing delay to guarantee 15 RPM compliance
            if idx < len(jobs) - 1:
                await asyncio.sleep(self.rate_limit_delay)

        # Record aggregate usage for this batch
        report = self.cost_tracker.get_report()
        if report["total_requests"] > 0:
            agg_usage = ClassificationUsage(
                id=uuid4(),
                collection_run_id=None,
                model_name=report["model_name"],
                total_input_tokens=report["total_input_tokens"],
                total_output_tokens=report["total_output_tokens"],
                total_requests=report["total_requests"],
                total_cost_usd=report["total_cost_usd"],
                pricing_config=report["pricing_config"],
            )
            self.db.add(agg_usage)
            await self.db.commit()

        counts = await self.get_backlog_counts()
        return {
            "status": "completed",
            "processed": processed_count,
            "classified": classified_count,
            "failed": failed_count,
            "model_name": report["model_name"],
            "total_input_tokens": report["total_input_tokens"],
            "total_output_tokens": report["total_output_tokens"],
            "estimated_cost_usd": report["total_cost_usd"],
            "remaining_backlog": counts["pending"] + counts["failed"],
            "counts": counts,
        }
