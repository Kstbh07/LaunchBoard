"""Arbeitnow Job Board API Collector.

Fetches tech and startup job postings from Arbeitnow's public API:
https://www.arbeitnow.com/api/job-board-api
Terms of service: Publicly available endpoint for job search & indexing.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class ArbeitnowCollector(BaseCollector):
    """Collector for Arbeitnow job board API."""

    name: str = "arbeitnow"
    base_url: str = "https://www.arbeitnow.com/api/job-board-api"
    rate_limit_delay: float = 1.0
    max_pages: int = 5

    async def collect(self) -> list[RawJob]:
        """Collect jobs across pages 1 to 3 from Arbeitnow API."""
        all_jobs: list[RawJob] = []
        seen_slugs: set[str] = set()

        for page in range(1, self.max_pages + 1):
            if page > 1:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}?page={page}"
            self.logger.info("fetching_page", page=page, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code != 200:
                    self.logger.warning(
                        "arbeitnow_fetch_failed",
                        status_code=response.status_code,
                        page=page,
                    )
                    break

                payload: dict[str, Any] = response.json()
                data_list = payload.get("data", [])
                if not isinstance(data_list, list):
                    self.logger.warning("unexpected_arbeitnow_data_format", page=page)
                    break

                if not data_list:
                    self.logger.info("arbeitnow_no_more_data", page=page)
                    break

                for item in data_list:
                    if not isinstance(item, dict):
                        continue

                    slug = str(item.get("slug") or "")
                    if slug and slug in seen_slugs:
                        continue
                    if slug:
                        seen_slugs.add(slug)

                    job = self._parse_job(item)
                    if job:
                        all_jobs.append(job)

            except httpx.HTTPError as exc:
                self.logger.error("arbeitnow_network_error", page=page, error=str(exc))
                self.errors.append(f"Network error page {page}: {exc}")
            except Exception as exc:
                self.logger.error("arbeitnow_parse_error", page=page, error=str(exc))
                self.errors.append(f"Parse error page {page}: {exc}")

        # Filter for India relevance and fresher/entry-level criteria
        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("arbeitnow_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a single Arbeitnow item into a RawJob."""
        title = item.get("title")
        company = item.get("company_name")
        url = item.get("url")
        if not title or not company or not url:
            return None

        description = self._clean_html(item.get("description", "")) or title
        is_remote = bool(item.get("remote", False))
        location = item.get("location") or ("Remote" if is_remote else None)

        raw_job_types = item.get("job_types", [])
        if isinstance(raw_job_types, list):
            joined = ", ".join(str(t).title() for t in raw_job_types if str(t).strip())
            # Map or truncate to fit VARCHAR(50)
            if len(joined) > 45:
                for std_type in ["Internship", "Full-time", "Part-time", "Contract"]:
                    if std_type.lower() in joined.lower():
                        employment_type = std_type
                        break
                else:
                    employment_type = joined[:45]
            else:
                employment_type = joined or None
        elif isinstance(raw_job_types, str):
            employment_type = raw_job_types.title()[:45]
        else:
            employment_type = None

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        tags = item.get("tags", [])
        skills = [str(tag).strip() for tag in tags if str(tag).strip()] if isinstance(tags, list) else []

        posted_at = self._parse_datetime(item.get("created_at"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type,
            experience_level=exp_level,
            application_url=url,
            source_name="Arbeitnow",
            source_url=url,
            source_job_id=str(item.get("slug")) if item.get("slug") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
