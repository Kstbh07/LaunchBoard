"""Adzuna Job Search API Collector.

Fetches job openings for India from Adzuna's public developer API:
https://developer.adzuna.com/
Requires ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables.
Gracefully skips execution when credentials are not configured.
"""
import asyncio
import os
from typing import Any, Optional
import urllib.parse

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class AdzunaCollector(BaseCollector):
    """Collector for Adzuna India job search API."""

    name: str = "adzuna"
    base_url: str = "https://api.adzuna.com/v1/api/jobs/in/search"
    rate_limit_delay: float = 1.0

    SEARCH_QUERIES = [
        "fresher intern junior",
        "graduate trainee",
        "entry level developer",
    ]

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.app_id = app_id or os.getenv("ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("ADZUNA_APP_KEY")

    async def collect(self) -> list[RawJob]:
        """Collect fresher and entry-level jobs from Adzuna India."""
        if not self.app_id or not self.app_key:
            self.logger.info(
                "adzuna_skipped_missing_credentials",
                message="ADZUNA_APP_ID or ADZUNA_APP_KEY not configured",
            )
            return []

        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for q_idx, query in enumerate(self.SEARCH_QUERIES):
            if q_idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            encoded_what = urllib.parse.quote_plus(query)
            # Fetch page 1 for each query
            url = (
                f"{self.base_url}/1"
                f"?app_id={self.app_id}&app_key={self.app_key}"
                f"&results_per_page=50&what={encoded_what}&max_days_old=30"
            )

            self.logger.info("fetching_adzuna", query=query, url=url.replace(self.app_key, "***"))

            try:
                response = await self.client.get(url)
                if response.status_code == 401 or response.status_code == 403:
                    self.logger.error("adzuna_auth_failed", status_code=response.status_code)
                    self.errors.append(f"Adzuna authentication failed (HTTP {response.status_code})")
                    break

                if response.status_code != 200:
                    self.logger.warning(
                        "adzuna_fetch_failed",
                        status_code=response.status_code,
                        query=query,
                    )
                    continue

                payload: dict[str, Any] = response.json()
                results = payload.get("results", [])
                if not isinstance(results, list):
                    self.logger.warning("unexpected_adzuna_format", query=query)
                    continue

                for item in results:
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
                self.logger.error("adzuna_network_error", query=query, error=str(exc))
                self.errors.append(f"Network error for query '{query}': {exc}")
            except Exception as exc:
                self.logger.error("adzuna_parse_error", query=query, error=str(exc))
                self.errors.append(f"Parse error for query '{query}': {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("adzuna_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert an Adzuna search result item to RawJob."""
        title = item.get("title")
        redirect_url = item.get("redirect_url")
        if not title or not redirect_url:
            return None

        # Company display name
        company_data = item.get("company")
        company = (
            company_data.get("display_name")
            if isinstance(company_data, dict)
            else "Unknown"
        ) or "Unknown"

        description = self._clean_html(item.get("description", "")) or title

        # Location
        location_data = item.get("location")
        if isinstance(location_data, dict):
            location = location_data.get("display_name") or "India"
        elif isinstance(location_data, str):
            location = location_data
        else:
            location = "India"

        # Check for remote indicators
        is_remote = (
            "remote" in (location or "").lower()
            or "remote" in title.lower()
            or "work from home" in description.lower()
        )

        # Employment type
        contract_time = item.get("contract_time")  # e.g., "full_time"
        contract_type = item.get("contract_type")  # e.g., "permanent"
        employment_type = (
            contract_time.replace("_", " ").title()
            if contract_time
            else (contract_type.title() if contract_type else None)
        )

        # Experience level
        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        # Skills from category
        skills: list[str] = []
        category_data = item.get("category")
        if isinstance(category_data, dict) and category_data.get("label"):
            skills.append(str(category_data["label"]).strip())

        posted_at = self._parse_datetime(item.get("created"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type,
            experience_level=exp_level,
            application_url=redirect_url,
            source_name="Adzuna",
            source_url=redirect_url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
