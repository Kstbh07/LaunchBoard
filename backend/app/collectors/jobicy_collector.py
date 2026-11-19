"""Jobicy Remote Jobs API v2 Collector.

Fetches remote listings from Jobicy's public API:
https://jobicy.com/api/v2/remote-jobs
Terms of service: Public API for remote job indexing.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class JobicyCollector(BaseCollector):
    """Collector for Jobicy Remote Jobs API v2."""

    name: str = "jobicy"
    base_url: str = "https://jobicy.com/api/v2/remote-jobs"
    rate_limit_delay: float = 1.0

    async def collect(self) -> list[RawJob]:
        """Collect and parse jobs from Jobicy public API."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        url = f"{self.base_url}?count=50"
        self.logger.info("fetching_jobicy_api", url=url)
        try:
            response = await self.client.get(url)
            if response.status_code != 200:
                self.logger.warning("jobicy_fetch_failed", status_code=response.status_code)
                self.errors.append(f"HTTP {response.status_code}")
                return []

            data = response.json()
            jobs_list = data.get("jobs", []) if isinstance(data, dict) else []

            for item in jobs_list:
                if not isinstance(item, dict):
                    continue

                job_id = str(item.get("id") or "")
                if job_id and job_id in seen_ids:
                    continue
                if job_id:
                    seen_ids.add(job_id)

                job = self._parse_job(item)
                if job:
                    all_jobs.append(job)

        except httpx.HTTPError as exc:
            self.logger.error("jobicy_network_error", error=str(exc))
            self.errors.append(f"Network error: {exc}")
        except Exception as exc:
            self.logger.error("jobicy_parse_error", error=str(exc))
            self.errors.append(f"Parse error: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("jobicy_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a Jobicy job item to RawJob."""
        title = item.get("jobTitle")
        company = item.get("companyName")
        url = item.get("url")
        if not title or not company or not url:
            return None

        raw_desc = item.get("jobDescription", "")
        description = self._clean_html(raw_desc) or title

        location = item.get("jobGeo") or "Remote"
        employment_type = item.get("jobType")
        if isinstance(employment_type, list):
            employment_type = ", ".join(str(t).title() for t in employment_type)
        elif isinstance(employment_type, str):
            employment_type = employment_type.title()

        categories = item.get("jobCategory") or []
        skills = [str(c).strip() for c in categories] if isinstance(categories, list) else ([str(categories)] if categories else [])

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        posted_at = self._parse_datetime(item.get("pubDate"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type[:45] if employment_type else None,
            experience_level=exp_level,
            application_url=url,
            source_name="Jobicy",
            source_url=url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=True,
            skills=skills,
        )
