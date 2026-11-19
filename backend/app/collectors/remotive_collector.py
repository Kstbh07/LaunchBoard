"""Remotive Job Board Collector.

Fetches remote listings from Remotive's public, free API:
https://remotive.com/api/remote-jobs
Terms of service: Free to access for non-commercial and job search aggregation.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class RemotiveCollector(BaseCollector):
    """Collector for Remotive public remote job listings."""

    name: str = "remotive"
    base_url: str = "https://remotive.com/api/remote-jobs"
    rate_limit_delay: float = 1.0

    CATEGORIES = [
        "software-dev",
        "data",
        "design",
        "product",
        "qa",
        "devops",
    ]

    JOB_TYPE_MAP = {
        "full_time": "Full-time",
        "contract": "Contract",
        "part_time": "Part-time",
        "freelance": "Freelance",
        "internship": "Internship",
    }

    async def collect(self) -> list[RawJob]:
        """Collect and parse jobs from Remotive API across relevant tech categories."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for idx, category in enumerate(self.CATEGORIES):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}?category={category}&limit=100"
            self.logger.info("fetching_category", category=category, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code != 200:
                    self.logger.warning(
                        "remotive_fetch_failed",
                        status_code=response.status_code,
                        category=category,
                    )
                    continue

                data: dict[str, Any] = response.json()
                raw_job_list = data.get("jobs", [])
                if not isinstance(raw_job_list, list):
                    self.logger.warning("unexpected_remotive_payload", category=category)
                    continue

                for item in raw_job_list:
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
                self.logger.error("remotive_network_error", category=category, error=str(exc))
                self.errors.append(f"Network error for {category}: {exc}")
            except Exception as exc:
                self.logger.error("remotive_parse_error", category=category, error=str(exc))
                self.errors.append(f"Parse error for {category}: {exc}")

        # Filter for India relevance and fresher/entry-level criteria
        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("remotive_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a single Remotive job JSON object to RawJob."""
        title = item.get("title")
        company = item.get("company_name")
        url = item.get("url")
        if not title or not company or not url:
            return None

        raw_desc = item.get("description", "")
        description = self._clean_html(raw_desc) or title

        location = item.get("candidate_required_location") or "Remote"
        job_type_raw = str(item.get("job_type") or "").strip().lower()
        employment_type = self.JOB_TYPE_MAP.get(job_type_raw, job_type_raw.title() if job_type_raw else None)

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        skills = [str(tag).strip() for tag in tags if str(tag).strip()]

        posted_at = self._parse_datetime(item.get("publication_date"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type,
            experience_level=exp_level,
            application_url=url,
            source_name="Remotive",
            source_url=url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=True,
            skills=skills,
        )
