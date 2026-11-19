"""Himalayas Remote Job Board Collector.

Fetches remote listings from Himalayas public jobs API:
https://himalayas.app/jobs/api
Terms of service: Public API for remote job indexing and discovery.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class HimalayasCollector(BaseCollector):
    """Collector for Himalayas remote job board API."""

    name: str = "himalayas"
    base_url: str = "https://himalayas.app/jobs/api"
    rate_limit_delay: float = 1.0
    limit: int = 100
    max_pages: int = 3

    async def collect(self) -> list[RawJob]:
        """Collect and parse jobs from Himalayas API with pagination."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for page in range(self.max_pages):
            offset = page * self.limit
            if page > 0:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}?limit={self.limit}&offset={offset}"
            self.logger.info("fetching_himalayas", offset=offset, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code != 200:
                    self.logger.warning(
                        "himalayas_fetch_failed",
                        status_code=response.status_code,
                        offset=offset,
                    )
                    break

                payload: Any = response.json()
                if isinstance(payload, dict):
                    raw_jobs = payload.get("jobs", [])
                elif isinstance(payload, list):
                    raw_jobs = payload
                else:
                    self.logger.warning("unexpected_himalayas_payload_type", payload_type=type(payload).__name__)
                    break

                if not raw_jobs:
                    self.logger.info("himalayas_no_more_jobs", offset=offset)
                    break

                for item in raw_jobs:
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
                self.logger.error("himalayas_network_error", offset=offset, error=str(exc))
                self.errors.append(f"Network error at offset {offset}: {exc}")
            except Exception as exc:
                self.logger.error("himalayas_parse_error", offset=offset, error=str(exc))
                self.errors.append(f"Parse error at offset {offset}: {exc}")

        # Filter for India relevance and fresher/entry-level criteria
        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("himalayas_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a Himalayas job entry to RawJob."""
        title = item.get("title")
        company = item.get("companyName")
        url = item.get("applicationLink")
        if not title or not company or not url:
            return None

        description = self._clean_html(item.get("description", "")) or title

        location_restrictions = item.get("locationRestrictions", [])
        if isinstance(location_restrictions, list) and location_restrictions:
            location = ", ".join(str(loc).strip() for loc in location_restrictions if str(loc).strip())
        else:
            location = "Remote"

        categories = item.get("categories", [])
        skills = [str(cat).strip() for cat in categories if str(cat).strip()] if isinstance(categories, list) else []

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
        )

        posted_at = self._parse_datetime(item.get("pubDate"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=None,
            experience_level=exp_level,
            application_url=url,
            source_name="Himalayas",
            source_url=url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=True,
            skills=skills,
        )
