"""RemoteOK Job Board API Collector.

Fetches remote listings from RemoteOK's public JSON API:
https://remoteok.com/api
Terms of service: Public endpoint for remote job discovery.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class RemoteokCollector(BaseCollector):
    """Collector for RemoteOK public API."""

    name: str = "remoteok"
    base_url: str = "https://remoteok.com/api"
    rate_limit_delay: float = 1.0

    async def collect(self) -> list[RawJob]:
        """Collect and parse jobs from RemoteOK public API."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        self.logger.info("fetching_remoteok", url=self.base_url)
        try:
            response = await self.client.get(
                self.base_url,
                headers={
                    "User-Agent": "LaunchBoard/2.0 (Job Aggregator; fresher-india-focus)",
                    "Accept": "application/json",
                },
            )
            if response.status_code != 200:
                self.logger.warning("remoteok_fetch_failed", status_code=response.status_code)
                self.errors.append(f"HTTP {response.status_code}")
                return []

            data = response.json()
            if not isinstance(data, list):
                self.logger.warning("unexpected_remoteok_payload")
                return []

            # RemoteOK's first item is legal/metadata disclaimer, actual jobs follow
            for item in data:
                if not isinstance(item, dict) or not item.get("id"):
                    continue

                job_id = str(item.get("id"))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                job = self._parse_job(item)
                if job:
                    all_jobs.append(job)

        except httpx.HTTPError as exc:
            self.logger.error("remoteok_network_error", error=str(exc))
            self.errors.append(f"Network error: {exc}")
        except Exception as exc:
            self.logger.error("remoteok_parse_error", error=str(exc))
            self.errors.append(f"Parse error: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("remoteok_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a RemoteOK job dictionary to RawJob."""
        title = item.get("position")
        company = item.get("company")
        url = item.get("url") or item.get("apply_url")
        if not title or not company or not url:
            return None

        # Clean description
        raw_desc = item.get("description", "")
        description = self._clean_html(raw_desc) or title

        location = item.get("location") or "Remote"
        tags = item.get("tags", [])
        skills = [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else []

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
        )

        posted_at = self._parse_datetime(item.get("date"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type="Full-time",
            experience_level=exp_level,
            application_url=url,
            source_name="RemoteOK",
            source_url=url,
            source_job_id=str(item.get("id")),
            posted_at=posted_at,
            is_remote=True,
            skills=skills,
        )
