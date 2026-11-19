"""Ashby Job Boards Collector.

Fetches public postings from Ashby's open job board API:
https://api.ashbyhq.com/posting-api/job-board/{company}
Terms of service: Public endpoint for candidate discovery.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class AshbyCollector(BaseCollector):
    """Collector for public Ashby board postings."""

    name: str = "ashby"
    base_url: str = "https://api.ashbyhq.com/posting-api/job-board"
    rate_limit_delay: float = 1.0

    COMPANIES: list[str] = [
        "cursor",
        "posthog",
        "linear",
        "sentry",
        "modal",
        "resend",
        "perplexity",
        "replit",
        "ramp",
        "notion",
    ]

    COMPANY_DISPLAY_NAMES: dict[str, str] = {
        "cursor": "Cursor (Anysphere)",
        "posthog": "PostHog",
        "linear": "Linear",
        "sentry": "Sentry",
        "modal": "Modal Labs",
        "resend": "Resend",
        "perplexity": "Perplexity AI",
        "replit": "Replit",
        "ramp": "Ramp",
        "notion": "Notion",
    }

    def __init__(self, companies: Optional[list[str]] = None) -> None:
        super().__init__()
        self.companies = companies or self.COMPANIES

    async def collect(self) -> list[RawJob]:
        """Collect and parse postings from Ashby boards."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for idx, company_slug in enumerate(self.companies):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}/{company_slug}"
            self.logger.info("fetching_ashby_board", company=company_slug, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code == 404:
                    self.logger.info("ashby_board_not_found", company=company_slug)
                    continue

                if response.status_code != 200:
                    self.logger.warning(
                        "ashby_fetch_failed",
                        company=company_slug,
                        status_code=response.status_code,
                    )
                    continue

                payload = response.json()
                raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

                for item in raw_jobs:
                    if not isinstance(item, dict):
                        continue

                    job_id = str(item.get("id") or "")
                    if job_id and job_id in seen_ids:
                        continue
                    if job_id:
                        seen_ids.add(job_id)

                    job = self._parse_job(item, company_slug)
                    if job:
                        all_jobs.append(job)

            except httpx.HTTPError as exc:
                self.logger.error("ashby_network_error", company=company_slug, error=str(exc))
                self.errors.append(f"Network error for {company_slug}: {exc}")
            except Exception as exc:
                self.logger.error("ashby_parse_error", company=company_slug, error=str(exc))
                self.errors.append(f"Parse error for {company_slug}: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("ashby_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any], company_slug: str) -> Optional[RawJob]:
        """Convert an Ashby job listing to RawJob."""
        title = item.get("title")
        app_url = item.get("jobUrl") or item.get("applyUrl")
        if not title or not app_url:
            return None

        company = self.COMPANY_DISPLAY_NAMES.get(company_slug, company_slug.title())

        # Description from plain text or HTML
        raw_desc = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
        description = self._clean_html(raw_desc) or title

        location = item.get("location") or "Remote"
        is_remote = bool(item.get("isRemote", False)) or "remote" in (location or "").lower()

        employment_type = item.get("employmentType")
        if employment_type:
            employment_type = str(employment_type).replace("_", " ").title()

        department = item.get("department")
        skills = [department] if department else []

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        posted_at = self._parse_datetime(item.get("publishedAt"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type[:45] if employment_type else None,
            experience_level=exp_level,
            application_url=app_url,
            source_name=f"Ashby:{company_slug}",
            source_url=app_url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
