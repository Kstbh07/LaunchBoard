"""SmartRecruiters Job Board Collector for Indian Tech Companies.

Fetches public job postings from SmartRecruiters open postings API for top Indian employers:
https://api.smartrecruiters.com/v1/companies/{company}/postings
Terms of service: SmartRecruiters public API is provided for open job discovery.
"""
import asyncio
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class SmartRecruitersCollector(BaseCollector):
    """Collector for public SmartRecruiters job boards of Indian tech employers."""

    name: str = "smartrecruiters"
    base_url: str = "https://api.smartrecruiters.com/v1/companies"
    rate_limit_delay: float = 0.5

    COMPANIES: list[str] = [
        "swiggy",
        "freshworks",
    ]

    COMPANY_DISPLAY_NAMES: dict[str, str] = {
        "swiggy": "Swiggy",
        "freshworks": "Freshworks",
    }

    def __init__(self, companies: Optional[list[str]] = None) -> None:
        super().__init__()
        self.companies = companies or self.COMPANIES

    async def collect(self) -> list[RawJob]:
        """Collect and parse postings from SmartRecruiters boards."""
        all_jobs: list[RawJob] = []
        seen_ids: set[str] = set()

        for idx, company_slug in enumerate(self.companies):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            display_name = self.COMPANY_DISPLAY_NAMES.get(
                company_slug, company_slug.capitalize()
            )
            self.logger.info("fetching_smartrecruiters_board", company=company_slug)

            offset = 0
            limit = 100
            company_raw_items: list[dict[str, Any]] = []

            while True:
                url = f"{self.base_url}/{company_slug}/postings?limit={limit}&offset={offset}"
                try:
                    response = await self.client.get(url)
                    if response.status_code == 404:
                        self.logger.info("smartrecruiters_board_not_found", company=company_slug)
                        break

                    if response.status_code != 200:
                        self.logger.warning(
                            "smartrecruiters_fetch_failed",
                            company=company_slug,
                            status=response.status_code,
                        )
                        self.errors.append(
                            f"{company_slug}: HTTP {response.status_code}"
                        )
                        break

                    data = response.json()
                    content = data.get("content", [])
                    if not content:
                        break

                    company_raw_items.extend(content)
                    total_found = data.get("totalFound", 0)
                    offset += limit
                    if offset >= total_found:
                        break

                    await asyncio.sleep(0.2)

                except Exception as exc:
                    self.logger.error(
                        "smartrecruiters_request_error",
                        company=company_slug,
                        error=str(exc),
                    )
                    self.errors.append(f"{company_slug}: {exc}")
                    break

            # Filter for India-based jobs first to minimize detail calls
            india_items: list[dict[str, Any]] = []
            for item in company_raw_items:
                loc = item.get("location") or {}
                country = (loc.get("country") or "").lower()
                full_loc = (loc.get("fullLocation") or "").lower()
                city = (loc.get("city") or "").lower()

                is_india = (
                    country == "in"
                    or "india" in full_loc
                    or any(
                        c in full_loc or c in city
                        for c in [
                            "bengaluru", "bangalore", "mumbai", "pune", "delhi",
                            "hyderabad", "chennai", "noida", "gurugram", "gurgaon",
                            "kolkata", "ahmedabad", "kochi", "chandigarh", "jaipur"
                        ]
                    )
                )
                if is_india:
                    india_items.append(item)

            self.logger.info(
                "smartrecruiters_india_postings_found",
                company=company_slug,
                total=len(company_raw_items),
                india=len(india_items),
            )

            # Concurrent detail fetch for India items to extract full job descriptions
            sem = asyncio.Semaphore(10)

            async def fetch_job_details(item: dict[str, Any]) -> Optional[RawJob]:
                job_id = str(item.get("id", ""))
                if not job_id or job_id in seen_ids:
                    return None
                seen_ids.add(job_id)

                title = (item.get("name") or "").strip()
                if not title:
                    return None

                loc = item.get("location") or {}
                city = loc.get("city") or ""
                region = loc.get("region") or ""
                full_loc = loc.get("fullLocation") or (f"{city}, India" if city else "India")
                is_remote = bool(loc.get("remote") or False)

                type_emp_label = (item.get("typeOfEmployment") or {}).get("label") or ""
                exp_label = (item.get("experienceLevel") or {}).get("label") or ""

                # Standardize employment type
                emp_type = "Full-time"
                if "intern" in type_emp_label.lower() or "intern" in title.lower():
                    emp_type = "Internship"
                elif "part" in type_emp_label.lower():
                    emp_type = "Part-time"
                elif "contract" in type_emp_label.lower():
                    emp_type = "Contract"

                # Standardize experience level
                exp_level: Optional[str] = None
                if "intern" in emp_type.lower():
                    exp_level = "Internship"
                elif "entry" in exp_label.lower() or "fresher" in title.lower() or "graduate" in title.lower():
                    exp_level = "Fresher" if "fresher" in title.lower() else "Entry-level"
                elif "mid" in exp_label.lower() or "senior" in exp_label.lower() or "executive" in exp_label.lower():
                    exp_level = "Experienced"

                posting_url = (
                    f"https://jobs.smartrecruiters.com/{display_name}/{job_id}"
                )

                description = ""
                async with sem:
                    try:
                        detail_url = f"{self.base_url}/{company_slug}/postings/{job_id}"
                        detail_res = await self.client.get(detail_url)
                        if detail_res.status_code == 200:
                            d = detail_res.json()
                            job_ad = d.get("jobAd", {}).get("sections", {})
                            parts = []
                            if job_ad.get("companyDescription", {}).get("text"):
                                parts.append(self._clean_html(job_ad["companyDescription"]["text"]))
                            if job_ad.get("jobDescription", {}).get("text"):
                                parts.append(self._clean_html(job_ad["jobDescription"]["text"]))
                            if job_ad.get("qualifications", {}).get("text"):
                                parts.append(self._clean_html(job_ad["qualifications"]["text"]))
                            if job_ad.get("additionalInformation", {}).get("text"):
                                parts.append(self._clean_html(job_ad["additionalInformation"]["text"]))
                            description = "\n\n".join(parts)
                    except Exception:
                        pass

                if not description:
                    # Fallback summary description
                    func_label = (item.get("function") or {}).get("label") or "Engineering"
                    ind_label = (item.get("industry") or {}).get("label") or "Technology"
                    description = f"{title} position at {display_name} in {full_loc}. Function: {func_label}. Industry: {ind_label}."

                posted_at = self._parse_datetime(item.get("releasedDate"))

                try:
                    return RawJob(
                        title=title,
                        company=display_name,
                        description=description,
                        location=full_loc,
                        employment_type=emp_type,
                        experience_level=exp_level,
                        application_url=posting_url,
                        source_name=f"SmartRecruiters:{company_slug}",
                        source_url=posting_url,
                        source_job_id=job_id,
                        posted_at=posted_at,
                        is_remote=is_remote,
                        skills=[],
                    )
                except Exception as val_err:
                    self.logger.warning("smartrecruiters_job_validation_error", error=str(val_err))
                    return None

            # Execute detail fetches
            parsed_jobs = await asyncio.gather(*[fetch_job_details(it) for it in india_items])
            for pj in parsed_jobs:
                if pj:
                    all_jobs.append(pj)

        self.logger.info("smartrecruiters_collection_completed", total_jobs=len(all_jobs))
        return all_jobs
