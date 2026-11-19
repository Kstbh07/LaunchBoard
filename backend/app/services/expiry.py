"""Job Freshness and Expiry Management Service.

Detects and expires outdated listings according to configurable expiry policy.
Ensures expired opportunities are not served on active job feeds.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.job import Job

logger = structlog.get_logger()

DEFAULT_EXPIRY_DAYS = 30


class ExpiryService:
    """Manages job listing lifecycles and expiration states."""

    def __init__(self, db: AsyncSession, expiry_days: int = DEFAULT_EXPIRY_DAYS) -> None:
        self.db = db
        self.expiry_days = expiry_days

    async def expire_stale_jobs(self) -> int:
        """Mark active jobs as expired if not verified/re-seen within expiry window.

        Returns:
            Number of jobs marked as expired.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.expiry_days)
        logger.info("running_job_expiry_check", cutoff=cutoff.isoformat(), days=self.expiry_days)

        stmt = (
            update(Job)
            .where(
                Job.status == "active",
                Job.last_verified_at < cutoff,
            )
            .values(
                status="expired",
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self.db.execute(stmt)
        expired_count = result.rowcount or 0
        if expired_count > 0:
            await self.db.commit()
            logger.info("stale_jobs_expired", count=expired_count)

        return expired_count

    async def get_freshness_stats(self) -> dict[str, int]:
        """Compile statistics on job freshness breakdown."""
        now = datetime.now(timezone.utc)
        d7 = now - timedelta(days=7)
        d14 = now - timedelta(days=14)
        d30 = now - timedelta(days=30)

        # Count active jobs verified in past 7, 14, 30 days
        q7 = select(func.count(Job.id)).where(Job.status == "active", Job.last_verified_at >= d7)
        q14 = select(func.count(Job.id)).where(Job.status == "active", Job.last_verified_at >= d14)
        q30 = select(func.count(Job.id)).where(Job.status == "active", Job.last_verified_at >= d30)
        q_expired = select(func.count(Job.id)).where(Job.status == "expired")

        return {
            "verified_past_7_days": (await self.db.execute(q7)).scalar() or 0,
            "verified_past_14_days": (await self.db.execute(q14)).scalar() or 0,
            "verified_past_30_days": (await self.db.execute(q30)).scalar() or 0,
            "total_expired_jobs": (await self.db.execute(q_expired)).scalar() or 0,
        }
