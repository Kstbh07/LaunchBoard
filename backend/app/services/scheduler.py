"""Automatic Refresh Scheduler Service for LaunchBoard.

Periodically runs the job aggregation and deduplication pipeline in the background.
Supports configurable interval (default 30 minutes), avoids overlapping runs,
and tracks execution telemetry.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

import structlog

from app.core.database import async_session_factory
from app.services.expiry import ExpiryService
from app.services.pipeline import CollectionPipeline

logger = structlog.get_logger()

DEFAULT_INTERVAL_SECONDS = 1800  # 30 minutes


class CollectionScheduler:
    """Singleton background task runner for periodic job collection."""

    def __init__(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> None:
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.is_running = False
        self.last_run_started_at: Optional[datetime] = None
        self.last_run_completed_at: Optional[datetime] = None
        self.next_run_at: Optional[datetime] = None
        self.total_scheduled_runs = 0

    def start(self) -> None:
        """Start the background scheduler task."""
        if self._task and not self._task.done():
            logger.info("scheduler_already_active")
            return

        self._stop_event.clear()
        self.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=self.interval_seconds)
        self._task = asyncio.create_task(self._loop(), name="launchboard-scheduler")
        logger.info(
            "scheduler_started",
            interval_seconds=self.interval_seconds,
            next_run_at=self.next_run_at.isoformat(),
        )

    async def stop(self) -> None:
        """Gracefully stop the background scheduler task."""
        if not self._task or self._task.done():
            return

        logger.info("stopping_scheduler")
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("scheduler_stopped")

    async def _loop(self) -> None:
        """Main loop that executes collection runs at the configured interval."""
        while not self._stop_event.is_set():
            try:
                # Wait for the interval or stop event
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
                break  # If stop event was set
            except asyncio.TimeoutError:
                # Timer fired, time to execute scheduled collection
                pass
            except asyncio.CancelledError:
                break

            if self._stop_event.is_set():
                break

            await self.run_once()

    async def run_once(self) -> Optional[dict[str, Any]]:
        """Execute a single scheduled collection run."""
        if self.is_running:
            logger.warning("scheduler_run_skipped_already_executing")
            return None

        self.is_running = True
        self.last_run_started_at = datetime.now(timezone.utc)
        self.total_scheduled_runs += 1
        run_id = uuid.uuid4()

        logger.info("scheduled_collection_starting", run_id=str(run_id))

        try:
            async with async_session_factory() as session:
                pipeline = CollectionPipeline(
                    db=session,
                    trigger_type="scheduled",
                    run_id=run_id,
                )
                stats = await pipeline.run()

                # Also run expiry check
                expiry_service = ExpiryService(db=session)
                expired_count = await expiry_service.expire_stale_jobs()
                if expired_count > 0:
                    stats["expired_jobs"] = expired_count

                self.last_run_completed_at = datetime.now(timezone.utc)
                self.next_run_at = self.last_run_completed_at + timedelta(seconds=self.interval_seconds)
                logger.info(
                    "scheduled_collection_completed",
                    run_id=str(run_id),
                    next_run_at=self.next_run_at.isoformat(),
                )
                return stats

        except Exception as exc:
            logger.error("scheduled_collection_failed", run_id=str(run_id), error=str(exc))
            return None
        finally:
            self.is_running = False

    def get_status(self) -> dict[str, Any]:
        """Return status telemetry for admin monitoring."""
        return {
            "interval_seconds": self.interval_seconds,
            "interval_minutes": round(self.interval_seconds / 60, 1),
            "is_running": self.is_running,
            "last_run_started_at": self.last_run_started_at.isoformat() if self.last_run_started_at else None,
            "last_run_completed_at": self.last_run_completed_at.isoformat() if self.last_run_completed_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "total_scheduled_runs": self.total_scheduled_runs,
        }


# Global scheduler singleton
scheduler = CollectionScheduler()
