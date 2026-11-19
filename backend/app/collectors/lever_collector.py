"""Lever Job Boards Collector.

Fetches public job postings from Lever's open postings API for top tech startups:
https://api.lever.co/v0/postings/{company}?mode=json
Terms of service: Public candidate discovery endpoint.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class LeverCollector(BaseCollector):
    """Collector for public Lever board postings."""

    name: str = "lever"
    base_url: str = "https://api.lever.co/v0/postings"
    rate_limit_delay: float = 1.0

    COMPANIES: list[str] = [
        "paytm",
        "meesho",
        "pocketfm",
        "cred",
        "zeta",
        "razorpay",
        "cred-club",
        "groww",
        "slice",
        "jupiter-money",
        "smallcase",
        "unacademy",
        "porter",
    ]

    COMPANY_DISPLAY_NAMES: dict[str, str] = {
        "paytm": "Paytm",
        "meesho": "Meesho",
        "pocketfm": "Pocket FM",
        "cred": "CRED",
        "zeta": "Zeta",
        "razorpay": "Razorpay",
        "cred-club": "CRED",
        "groww": "Groww",
        "slice": "Slice",
        "jupiter-money": "Jupiter Money",
        "smallcase": "smallcase",
        "unacademy": "Unacademy",
        "porter": "Porter",
    }

    def __init__(self, companies: Optional[list[str]] = None) -> None:
        super().__init__()
        self.companies = companies or self.COMPANIES

    async def collect(self) -> list[RawJob]:
        """Collect and parse postings from Lever boards."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for idx, company_slug in enumerate(self.companies):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            url = f"{self.base_url}/{company_slug}?mode=json"
            self.logger.info("fetching_lever_board", company=company_slug, url=url)

            try:
                response = await self.client.get(url)
                if response.status_code == 404:
                    self.logger.info("lever_board_not_found", company=company_slug)
                    continue

                if response.status_code != 200:
                    self.logger.warning(
                        "lever_fetch_failed",
                        company=company_slug,
                        status_code=response.status_code,
                    )
                    continue

                raw_jobs = response.json()
                if not isinstance(raw_jobs, list):
                    self.logger.warning("unexpected_lever_payload_type", company=company_slug)
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
                self.logger.error("lever_network_error", company=company_slug, error=str(exc))
                self.errors.append(f"Network error for {company_slug}: {exc}")
            except Exception as exc:
                self.logger.error("lever_parse_error", company=company_slug, error=str(exc))
                self.errors.append(f"Parse error for {company_slug}: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("lever_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any], company_slug: str) -> Optional[RawJob]:
        """Convert a Lever posting object to RawJob."""
        title = item.get("text")
        app_url = item.get("applyUrl") or item.get("hostedUrl")
        if not title or not app_url:
            return None

        company = self.COMPANY_DISPLAY_NAMES.get(
            company_slug, company_slug.replace("-", " ").title()
        )

        # Description
        raw_desc = item.get("descriptionPlain") or item.get("description") or ""
        description = self._clean_html(raw_desc) or title

        # Categories
        categories = item.get("categories") or {}
        location = categories.get("location") if isinstance(categories, dict) else None
        team = categories.get("team") if isinstance(categories, dict) else None
        commitment = categories.get("commitment") if isinstance(categories, dict) else None

        # Workplace type (e.g., "remote", "hybrid", "onsite")
        workplace_type = str(item.get("workplaceType") or "").lower()
        is_remote = (
            workplace_type == "remote"
            or "remote" in (location or "").lower()
            or "remote" in title.lower()
        )

        # Skills from team / department
        skills: list[str] = []
        if team:
            skills.append(str(team).strip())
        department = categories.get("department") if isinstance(categories, dict) else None
        if department and department != team:
            skills.append(str(department).strip())

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=commitment,
        )

        posted_at = self._parse_datetime(item.get("createdAt"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=commitment,
            experience_level=exp_level,
            application_url=app_url,
            source_name=f"Lever:{company_slug}",
            source_url=item.get("hostedUrl") or app_url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
