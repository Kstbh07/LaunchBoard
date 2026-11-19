"""FindWork.dev API Collector.

Fetches developer and tech jobs from the FindWork.dev REST API:
https://findwork.dev/developers/
Requires FINDWORK_API_KEY environment variable (Token auth).
Gracefully skips execution if the API key is not configured.
"""
import os
from typing import Any, Optional
import urllib.parse

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class FindworkCollector(BaseCollector):
    """Collector for FindWork.dev API."""

    name: str = "findwork"
    base_url: str = "https://findwork.dev/api/jobs/"
    rate_limit_delay: float = 1.0

    def __init__(self, api_key: Optional[str] = None) -> None:
        super().__init__()
        self.api_key = api_key or os.getenv("FINDWORK_API_KEY")

    async def collect(self) -> list[RawJob]:
        """Collect fresher and junior jobs in India from FindWork.dev."""
        if not self.api_key:
            self.logger.info(
                "findwork_skipped_missing_api_key",
                message="FINDWORK_API_KEY not configured",
            )
            return []

        params = {
            "location": "india",
            "search": "junior intern",
            "sort_by": "relevance",
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query_string}"
        headers = {"Authorization": f"Token {self.api_key}"}

        self.logger.info("fetching_findwork", url=url)
        all_jobs: list[RawJob] = []

        try:
            response = await self.client.get(url, headers=headers)
            if response.status_code in (401, 403):
                self.logger.error("findwork_auth_failed", status_code=response.status_code)
                self.errors.append(f"FindWork authentication failed (HTTP {response.status_code})")
                return []

            if response.status_code != 200:
                self.logger.warning("findwork_fetch_failed", status_code=response.status_code)
                return []

            payload: dict[str, Any] = response.json()
            results = payload.get("results", [])
            if not isinstance(results, list):
                self.logger.warning("unexpected_findwork_payload")
                return []

            for item in results:
                if not isinstance(item, dict):
                    continue

                job = self._parse_job(item)
                if job:
                    all_jobs.append(job)

        except httpx.HTTPError as exc:
            self.logger.error("findwork_network_error", error=str(exc))
            self.errors.append(f"Network error: {exc}")
        except Exception as exc:
            self.logger.error("findwork_parse_error", error=str(exc))
            self.errors.append(f"Parse error: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("findwork_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_job(self, item: dict[str, Any]) -> Optional[RawJob]:
        """Convert a FindWork result object to RawJob."""
        title = item.get("role")
        company = item.get("company_name")
        url = item.get("url")
        if not title or not company or not url:
            return None

        description = self._clean_html(item.get("text", "")) or title
        location = item.get("location") or "India"
        is_remote = bool(item.get("remote", False))
        employment_type = item.get("employment_type")

        keywords = item.get("keywords", [])
        skills = [str(k).strip() for k in keywords if str(k).strip()] if isinstance(keywords, list) else []

        exp_level = self._detect_experience_level(
            title=title,
            description=description,
            employment_type=employment_type,
        )

        posted_at = self._parse_datetime(item.get("date_posted"))

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type,
            experience_level=exp_level,
            application_url=url,
            source_name="FindWork",
            source_url=url,
            source_job_id=str(item.get("id")) if item.get("id") else None,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )
