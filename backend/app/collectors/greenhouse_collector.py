"""Greenhouse Job Boards Collector.

Fetches public postings from Greenhouse's open boards API for top Indian tech companies:
https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
Terms of service: Greenhouse public job board endpoints are exposed for candidate discovery.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class GreenhouseCollector(BaseCollector):
    """Collector for public Greenhouse board postings."""

    name: str = "greenhouse"
    base_url: str = "https://boards-api.greenhouse.io/v1/boards"
    rate_limit_delay: float = 1.0

    COMPANIES: list[str] = [
        "groww",
        "canonical",
        "stripe",
        "elastic",
        "gitlab",
        "mongodb",
        "cloudflare",
        "datadog",
        "inmobi",
        "rubrik",
        "hackerrank",
        "observeai",
        "slice",
        "highradius",
        "razorpay",
        "cred",
        "zomato",
        "swiggy",
        "meesho",
        "zerodha",
        "postman",
        "browserstack",
        "freshworks",
        "chargebee",
        "clevertap",
        "hasura",
        "wingify",
    ]

    COMPANY_DISPLAY_NAMES: dict[str, str] = {
        "groww": "Groww",
        "canonical": "Canonical",
        "stripe": "Stripe",
        "elastic": "Elastic",
        "gitlab": "GitLab",
        "mongodb": "MongoDB",
        "cloudflare": "Cloudflare",
        "datadog": "Datadog",
        "inmobi": "InMobi",
        "rubrik": "Rubrik",
        "hackerrank": "HackerRank",
        "observeai": "Observe.ai",
        "slice": "Slice",
        "highradius": "HighRadius",
        "razorpay": "Razorpay",
        "cred": "CRED",
        "zomato": "Zomato",
        "swiggy": "Swiggy",
        "meesho": "Meesho",
        "zerodha": "Zerodha",
        "postman": "Postman",
        "browserstack": "BrowserStack",
        "freshworks": "Freshworks",
        "chargebee": "Chargebee",
        "clevertap": "CleverTap",
        "hasura": "Hasura",
        "wingify": "Wingify",
    }

    def __init__(self, companies: Optional[list[str]] = None) -> None:
        super().__init__()
        self.companies = companies or self.COMPANIES

    async def collect(self) -> list[RawJob]:
        """Collect and parse postings from Greenhouse boards of Indian tech companies."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for idx, company_slug in enumerate(self.companies):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}/{company_slug}/jobs?content=true"
            self.logger.info("fetching_greenhouse_board", company=company_slug, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code == 404:
                    self.logger.info("greenhouse_board_not_found", company=company_slug)
                    continue

                if response.status_code != 200:
                    self.logger.warning(
                        "greenhouse_fetch_failed",
                        company=company_slug,
                        status_code=response.status_code,
                    )
                    continue

                payload: Any = response.json()
                raw_jobs: list[dict[str, Any]] = []
                if isinstance(payload, dict):
                    raw_jobs = payload.get("jobs", [])
                elif isinstance(payload, list):
                    raw_jobs = payload

                if not isinstance(raw_jobs, list):
                    self.logger.warning("unexpected_greenhouse_payload", company=company_slug)
                    continue

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
                self.logger.error("greenhouse_network_error", company=company_slug, error=str(exc))
                self.errors.append(f"Network error for {company_slug}: {exc}")
            except Exception as exc:
                self.logger.error("greenhouse_parse_error", company=company_slug, error=str(exc))
                self.errors.append(f"Parse error for {company_slug}: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("greenhouse_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any], company_slug: str) -> Optional[RawJob]:
        """Convert a Greenhouse job listing to RawJob."""
        title = item.get("title")
        app_url = item.get("absolute_url")
        if not title or not app_url:
            return None

        company = self.COMPANY_DISPLAY_NAMES.get(company_slug, company_slug.title())

        # Description from content field
        raw_content = item.get("content") or ""
        description = self._clean_html(raw_content) or title

        # Location
        location_data = item.get("location")
        location = ""
        if isinstance(location_data, dict):
            location = location_data.get("name") or ""
        elif isinstance(location_data, str):
            location = location_data

        is_remote = "remote" in (location or "").lower() or "remote" in title.lower()

        # Departments and metadata
        departments = item.get("departments", [])
        skills: list[str] = []
        if isinstance(departments, list):
            for dept in departments:
                if isinstance(dept, dict) and dept.get("name"):
                    skills.append(str(dept["name"]).strip())

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
        )

        posted_at = self._parse_datetime(item.get("updated_at"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location or None,
            employment_type=None,
            experience_level=exp_level,
            application_url=app_url,
            source_name=f"Greenhouse:{company_slug}",
            source_url=app_url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
