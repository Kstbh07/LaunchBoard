"""Collection Pipeline Orchestrator.

Orchestrates the full data collection, deduplication, and classification pipeline.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.collectors import get_all_collectors
from app.core.config import get_settings
from app.models import (
    Classification,
    ClassificationUsage,
    CollectionRun,
    Job,
    JobSource,
    SourceStatus,
)
from app.schemas.collector import RawJob
from app.services.classifier import ClassificationService
from app.services.cost_tracker import CostTracker
from app.services.deduplication import DeduplicationService, generate_fingerprint

logger = structlog.get_logger()


class CollectionPipeline:
    """Coordinates scraping from collectors, deduplication, persistence, and AI classification."""

    def __init__(
        self,
        db: AsyncSession,
        trigger_type: str = "manual",
        sources: Optional[Sequence[str]] = None,
        run_id: Optional[UUID] = None,
    ) -> None:
        self.db = db
        self.trigger_type = trigger_type
        self.sources = sources
        self.dedup_service = DeduplicationService()
        self.classifier = ClassificationService()
        self.cost_tracker = CostTracker(self.classifier.model_name)
        self.run_id = run_id or uuid4()
        self.stats: dict[str, Any] = {
            "total_fetched": 0,
            "total_new": 0,
            "total_updated": 0,
            "total_duplicates": 0,
            "total_classified": 0,
            "total_failed": 0,
            "total_errors": 0,
            "error_details": [],
            "source_results": {},
        }

    async def run(self) -> dict[str, Any]:
        """Execute the full collection and classification pipeline.

        Returns:
            Dictionary containing pipeline execution telemetry and stats.
        """
        # 1. Create collection run record in running state if not already created
        existing_run = await self.db.get(CollectionRun, self.run_id)
        if not existing_run:
            run_record = CollectionRun(
                id=self.run_id,
                trigger_type=self.trigger_type,
                status="running",
            )
            self.db.add(run_record)
            await self.db.commit()

        try:
            # 2. Collect from all enabled sources
            all_jobs = await self._collect_all_sources()
            self.stats["total_fetched"] = len(all_jobs)

            # 3. Get existing fingerprints from database
            existing_fps = await self._get_existing_fingerprints()

            # 4. Deduplicate
            new_jobs, updated_jobs, dup_count = self.dedup_service.process(
                all_jobs, existing_fps
            )
            self.stats["total_new"] = len(new_jobs)
            self.stats["total_updated"] = len(updated_jobs)
            self.stats["total_duplicates"] = dup_count

            # 5. Save new jobs to DB
            saved_jobs = await self._save_new_jobs(new_jobs)

            # 6. Update verified timestamps for re-seen jobs
            await self._update_verified_jobs(updated_jobs)

            # 7. Classify new and pending jobs (up to 30 per run for balanced execution time)
            jobs_to_classify = list(saved_jobs)
            if len(jobs_to_classify) < 30:
                pending_query = (
                    select(Job)
                    .where(Job.classification_status == "pending")
                    .limit(30 - len(jobs_to_classify))
                )
                pending_result = await self.db.execute(pending_query)
                for pj in pending_result.scalars().all():
                    if pj.id not in {j.id for j in jobs_to_classify}:
                        jobs_to_classify.append(pj)

            classified_count = await self._classify_jobs(jobs_to_classify[:30])
            self.stats["total_classified"] = classified_count

            # 8. Record usage telemetry and estimated costs
            await self._record_usage()

            # 9. Update run status
            run_status = "completed" if self.stats["total_errors"] == 0 else "partial"
            await self._update_run(run_status)
            self.stats["status"] = run_status

            return self.stats

        except Exception as e:
            logger.error("pipeline_failed", error=str(e), run_id=str(self.run_id))
            self.stats["error_details"].append(str(e))
            self.stats["total_errors"] += 1
            try:
                await self.db.rollback()
                await self._update_run("failed")
            except Exception as update_err:
                logger.error("failed_to_update_run_status", error=str(update_err))
            raise

    async def _collect_all_sources(self) -> list[RawJob]:
        """Collect jobs across all configured collectors."""
        collectors = get_all_collectors(self.sources)
        all_jobs: list[RawJob] = []

        for collector in collectors:
            try:
                jobs = await collector.safe_collect()
                self.stats["source_results"][collector.name] = {
                    "fetched": len(jobs),
                    "errors": collector.errors,
                    "status": "success" if not collector.errors else "partial",
                }
                all_jobs.extend(jobs)

                # Update operational status tracking for this source
                await self._update_source_status(collector.name, len(jobs), collector.errors)

            except Exception as e:
                logger.error("source_collection_failed", source=collector.name, error=str(e))
                self.stats["source_results"][collector.name] = {
                    "fetched": 0,
                    "errors": [str(e)],
                    "status": "failed",
                }
                self.stats["total_errors"] += 1
                self.stats["error_details"].append(f"{collector.name}: {e}")
                await self._update_source_status(collector.name, 0, [str(e)])

        return all_jobs

    async def _get_existing_fingerprints(self) -> set[str]:
        """Get all existing job fingerprints from database."""
        result = await self.db.execute(
            select(Job.fingerprint).where(Job.fingerprint.isnot(None))
        )
        return {row[0] for row in result.fetchall()}

    @staticmethod
    def _extract_initial_city(location: Optional[str], is_remote: bool) -> Optional[str]:
        if not location:
            return "Remote" if is_remote else None
        loc_lower = location.lower()
        mapping = {
            "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
            "mumbai": "Mumbai", "bombay": "Mumbai",
            "hyderabad": "Hyderabad", "pune": "Pune",
            "chennai": "Chennai", "madras": "Chennai",
            "delhi": "Delhi", "new delhi": "Delhi",
            "noida": "Noida", "gurgaon": "Gurugram", "gurugram": "Gurugram",
            "kolkata": "Kolkata", "ahmedabad": "Ahmedabad",
            "jaipur": "Jaipur", "chandigarh": "Chandigarh",
            "kochi": "Kochi", "coimbatore": "Coimbatore",
            "indore": "Indore", "bhopal": "Bhopal",
        }
        for k, v in mapping.items():
            if k in loc_lower:
                return v
        return "Remote" if is_remote else "Unknown"

    @staticmethod
    def _extract_initial_role(title: str) -> Optional[str]:
        t_lower = title.lower()
        if any(kw in t_lower for kw in ["frontend", "react", "vue", "angular", "ui"]):
            return "Frontend Development"
        if any(kw in t_lower for kw in ["backend", "python", "java", "golang", "node", "django", "fastapi"]):
            return "Backend Development"
        if any(kw in t_lower for kw in ["full stack", "fullstack", "software engineer", "sde", "developer"]):
            return "Full Stack Development"
        if any(kw in t_lower for kw in ["data analyst", "analytics", "bi developer"]):
            return "Data Analytics"
        if any(kw in t_lower for kw in ["data science", "data scientist", "machine learning", "ai", "ml"]):
            return "AI/ML Engineering"
        if any(kw in t_lower for kw in ["devops", "cloud", "aws", "kubernetes", "docker", "sre"]):
            return "DevOps / Cloud"
        if any(kw in t_lower for kw in ["qa", "test", "quality assurance", "sdet"]):
            return "QA / Testing"
        if any(kw in t_lower for kw in ["design", "ux", "product design"]):
            return "UI/UX Design"
        if any(kw in t_lower for kw in ["product manager", "product management", "associate product"]):
            return "Product Management"
        return "Software Development"

    async def _save_new_jobs(self, jobs: list[RawJob]) -> list[Job]:
        """Save newly discovered unique jobs and their source provenance to database."""
        # Query existing source keys to strictly prevent duplicate key constraint violations
        existing_sources_res = await self.db.execute(
            select(JobSource.source_name, JobSource.source_job_id).where(
                JobSource.source_job_id.isnot(None)
            )
        )
        existing_source_keys = set(existing_sources_res.fetchall())

        saved: list[Job] = []
        for raw_job in jobs:
            safe_source_name = raw_job.source_name[:195]
            safe_source_job_id = raw_job.source_job_id[:495] if raw_job.source_job_id else None

            # Skip if exact source posting already exists in DB or current batch
            if safe_source_job_id and (safe_source_name, safe_source_job_id) in existing_source_keys:
                self.stats["total_duplicates"] += 1
                logger.debug(
                    "duplicate_job_source_key_skipped",
                    source=safe_source_name,
                    source_job_id=safe_source_job_id,
                )
                continue

            fp = generate_fingerprint(raw_job.company, raw_job.title, raw_job.location)
            job_id = uuid4()
            city = self._extract_initial_city(raw_job.location, raw_job.is_remote)
            role = self._extract_initial_role(raw_job.title)
            # Defensive length limits matching PostgreSQL VARCHAR constraints
            safe_emp_type = raw_job.employment_type[:45] if raw_job.employment_type else None
            safe_exp_level = raw_job.experience_level[:45] if raw_job.experience_level else None
            safe_location = raw_job.location[:295] if raw_job.location else None
            safe_title = raw_job.title[:495]
            safe_company = raw_job.company[:295]
            safe_app_url = raw_job.application_url[:1990]
            safe_source_url = raw_job.source_url[:1990] if raw_job.source_url else None
            safe_city = city[:195] if city else None
            safe_role = role[:95] if role else None

            job = Job(
                id=job_id,
                title=safe_title,
                company=safe_company,
                description=raw_job.description,
                location=safe_location,
                city=safe_city,
                role_category=safe_role,
                employment_type=safe_emp_type,
                experience_level=safe_exp_level,
                application_url=safe_app_url,
                source_name=safe_source_name,
                source_url=safe_source_url,
                posted_at=raw_job.posted_at,
                is_remote=raw_job.is_remote,
                skills=raw_job.skills,
                fingerprint=fp,
                status="active",
                classification_status="pending",
            )
            self.db.add(job)
            saved.append(job)

            # Provenance record in job_sources
            source = JobSource(
                id=uuid4(),
                job_id=job_id,
                source_name=safe_source_name,
                source_url=safe_source_url,
                source_job_id=safe_source_job_id,
                application_url=safe_app_url,
                is_primary=True,
            )
            self.db.add(source)
            if safe_source_job_id:
                existing_source_keys.add((safe_source_name, safe_source_job_id))

        if saved:
            await self.db.commit()
        return saved

    async def _update_verified_jobs(self, jobs: list[RawJob]) -> None:
        """Update last_verified_at timestamp for re-seen active jobs."""
        if not jobs:
            return
        now = datetime.now(timezone.utc)
        for raw_job in jobs:
            fp = generate_fingerprint(raw_job.company, raw_job.title, raw_job.location)
            await self.db.execute(
                update(Job).where(Job.fingerprint == fp).values(last_verified_at=now)
            )
        await self.db.commit()

    async def _classify_jobs(self, jobs: list[Job]) -> int:
        """Classify newly added jobs using the configured AI classifier."""
        if not self.classifier.available:
            logger.warning("skipping_classification", reason="API not configured")
            return 0

        classified = 0
        for job in jobs:
            try:
                result, usage = await self.classifier.classify_job(
                    title=job.title,
                    company=job.company,
                    description=job.description,
                    location=job.location,
                )

                if result:
                    # Update job attributes with structured classification output
                    safe_role = result.role_category[:95] if result.role_category else None
                    safe_city = result.city[:195] if result.city else None
                    safe_exp = result.experience_level[:45] if result.experience_level else None
                    safe_emp = result.employment_type[:45] if result.employment_type else None

                    job.role_category = safe_role
                    job.city = safe_city
                    job.skills = result.skills
                    job.experience_level = safe_exp
                    job.employment_type = safe_emp
                    job.is_remote = result.is_remote
                    job.classification_confidence = result.confidence

                    confidence_level = self.classifier.get_confidence_level(result.confidence)
                    job.classification_status = (
                        "classified"
                        if confidence_level == "high"
                        else "review"
                        if confidence_level == "medium"
                        else "uncertain"
                    )

                    # Persist classification log record
                    classification = Classification(
                        id=uuid4(),
                        job_id=job.id,
                        model_name=usage.get("model_name", self.classifier.model_name)[:95],
                        role_category=safe_role,
                        city=safe_city,
                        skills=result.skills,
                        experience_level=safe_exp,
                        employment_type=safe_emp,
                        is_remote=result.is_remote,
                        confidence=result.confidence,
                        raw_response=result.model_dump_json(),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        processing_time_ms=usage.get("processing_time_ms", 0),
                        status="success",
                    )
                    self.db.add(classification)

                    # Track token usage and estimated cost
                    self.cost_tracker.record_usage(
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                    classified += 1
                else:
                    job.classification_status = "failed"
                    self.stats["total_failed"] += 1

                    classification = Classification(
                        id=uuid4(),
                        job_id=job.id,
                        model_name=usage.get("model_name", self.classifier.model_name),
                        status="failed",
                        raw_response=usage.get("error", "Classification failed"),
                        processing_time_ms=usage.get("processing_time_ms", 0),
                    )
                    self.db.add(classification)

            except Exception as e:
                logger.error("job_classification_error", job_id=str(job.id), error=str(e))
                job.classification_status = "failed"
                self.stats["total_failed"] += 1

            # Incremental commit so progress is never lost if interrupted
            await self.db.commit()
            # Rate limiting delay between LLM calls to comply with 15 RPM free-tier limit (14.28 RPM)
            await asyncio.sleep(4.2)

        return classified

    async def _record_usage(self) -> None:
        """Record aggregate classification usage and cost for this collection run."""
        report = self.cost_tracker.get_report()
        usage = ClassificationUsage(
            id=uuid4(),
            collection_run_id=self.run_id,
            model_name=report["model_name"],
            total_input_tokens=report["total_input_tokens"],
            total_output_tokens=report["total_output_tokens"],
            total_requests=report["total_requests"],
            total_cost_usd=report["total_cost_usd"],
            pricing_config=report["pricing_config"],
        )
        self.db.add(usage)
        await self.db.commit()

    async def _update_source_status(
        self,
        source_name: str,
        jobs_count: int,
        errors: list[str],
    ) -> None:
        """Update source health, uptime, and failure metrics."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(SourceStatus).where(SourceStatus.source_name == source_name)
        )
        status = result.scalar_one_or_none()

        if status:
            status.total_runs += 1
            status.total_jobs_collected += jobs_count
            if errors:
                status.last_failure_at = now
                status.last_error_message = "; ".join(errors)
                status.total_failures += 1
                status.consecutive_failures += 1
            else:
                status.last_success_at = now
                status.consecutive_failures = 0
                status.last_error_message = None
        else:
            status = SourceStatus(
                id=uuid4(),
                source_name=source_name,
                last_success_at=now if not errors else None,
                last_failure_at=now if errors else None,
                last_error_message="; ".join(errors) if errors else None,
                total_jobs_collected=jobs_count,
                total_runs=1,
                total_failures=1 if errors else 0,
                consecutive_failures=1 if errors else 0,
            )
            self.db.add(status)

        await self.db.commit()

    async def _update_run(self, status: str) -> None:
        """Update collection run completion record."""
        await self.db.execute(
            update(CollectionRun)
            .where(CollectionRun.id == self.run_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                total_fetched=self.stats["total_fetched"],
                total_new=self.stats["total_new"],
                total_updated=self.stats["total_updated"],
                total_duplicates=self.stats["total_duplicates"],
                total_classified=self.stats["total_classified"],
                total_failed=self.stats["total_failed"],
                total_errors=self.stats["total_errors"],
                error_details=self.stats["error_details"],
                source_results=self.stats["source_results"],
            )
        )
        await self.db.commit()
