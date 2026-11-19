"""Abstract base collector interface."""
import abc
from datetime import datetime, timezone
import html
import re
from typing import Any, Optional

import httpx
from pydantic import ValidationError
import structlog

from app.schemas.collector import RawJob

logger = structlog.get_logger()


class BaseCollector(abc.ABC):
    """Base class for all job collectors."""

    name: str = "base"
    base_url: str = ""
    rate_limit_delay: float = 1.0  # seconds between requests

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "LaunchBoard/1.0 (Job Aggregator; +https://github.com/launchboard)"
            },
            follow_redirects=True,
        )
        self.logger = logger.bind(collector=self.name)
        self.errors: list[str] = []
        self.stats = {"fetched": 0, "valid": 0, "errors": 0}

    @abc.abstractmethod
    async def collect(self) -> list[RawJob]:
        """Collect jobs from this source. Must be implemented by subclasses."""
        ...

    async def safe_collect(self) -> list[RawJob]:
        """Wrapper that catches exceptions and logs errors."""
        try:
            if self.client.is_closed:
                self.client = httpx.AsyncClient(
                    timeout=30.0,
                    headers={
                        "User-Agent": "LaunchBoard/1.0 (Job Aggregator; +https://github.com/launchboard)"
                    },
                    follow_redirects=True,
                )
            self.logger.info("starting_collection")
            jobs = await self.collect()
            self.stats["valid"] = len(jobs)
            self.logger.info("collection_complete", total=len(jobs))
            return jobs
        except Exception as e:
            self.logger.error("collection_failed", error=str(e))
            self.errors.append(str(e))
            self.stats["errors"] += 1
            return []
        finally:
            await self.client.aclose()

    def _filter_fresher_india(self, jobs: list[RawJob]) -> list[RawJob]:
        """Filter for India-based and fresher/entry-level/intern jobs."""
        india_cities = {
            "bengaluru", "bangalore", "mumbai", "delhi", "new delhi", "hyderabad",
            "chennai", "pune", "kolkata", "ahmedabad", "jaipur", "lucknow",
            "chandigarh", "indore", "nagpur", "bhopal", "visakhapatnam",
            "kochi", "coimbatore", "thiruvananthapuram", "gurgaon", "gurugram",
            "noida", "greater noida", "ghaziabad", "faridabad", "mysore",
            "mysuru", "mangalore", "mangaluru", "surat", "vadodara",
            "rajkot", "patna", "ranchi", "bhubaneswar", "guwahati",
            "dehradun", "agra", "varanasi", "allahabad", "prayagraj",
            "kanpur", "meerut", "jodhpur", "udaipur", "amritsar",
            "ludhiana", "jalandhar", "shimla", "srinagar", "jammu",
            "india", "remote - india", "anywhere in india",
        }
        fresher_keywords = {
            "fresher", "intern", "internship", "entry level", "entry-level",
            "junior", "graduate", "trainee", "apprentice", "0-1 year",
            "0-2 year", "no experience",
        }

        filtered = []
        for job in jobs:
            loc = (job.location or "").lower()
            title_lower = job.title.lower()
            desc_lower = (job.description or "").lower()[:500]

            # Check if India-related
            is_india = any(city in loc for city in india_cities)
            is_india = is_india or "india" in loc
            is_india = is_india or any(city in desc_lower for city in india_cities)

            # For remote jobs, include if they don't restrict to non-India
            if job.is_remote and not is_india:
                # Include remote jobs that don't specify a country, or mention India
                if not any(
                    country in loc
                    for country in [
                        "usa", "us only", "uk only", "europe only", "canada only",
                        "north america", "us/canada", "us remote", "us based",
                    ]
                ):
                    is_india = True  # Remote jobs open to anyone

            if not is_india:
                continue

            # Check if fresher/entry-level
            is_fresher = any(kw in title_lower or kw in desc_lower for kw in fresher_keywords)
            is_fresher = is_fresher or job.experience_level in ("Fresher", "Internship", "Entry-level")
            is_fresher = is_fresher or job.employment_type == "Internship"

            # Also include jobs that don't specify experience (could be fresher-friendly)
            if is_fresher or job.experience_level is None:
                filtered.append(job)

        return filtered

    @staticmethod
    def _clean_html(text: Optional[str]) -> str:
        """Strip HTML tags, decode entities, and normalize whitespace."""
        if not text:
            return ""
        # Convert line-breaking elements to newlines
        formatted = re.sub(r"<(?:br|p|div|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
        # Strip all HTML tags
        stripped = re.sub(r"<[^>]+>", " ", formatted)
        # Unescape HTML entities
        unescaped = html.unescape(stripped)
        # Normalize whitespace while preserving line breaks
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in unescaped.split("\n")]
        return "\n".join(line for line in lines if line).strip()

    @staticmethod
    def _parse_datetime(val: Any) -> Optional[datetime]:
        """Parse various date/time representations to timezone-aware UTC datetime."""
        if val is None:
            return None
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc)
        if isinstance(val, (int, float)):
            try:
                ts = float(val)
                # Check for timestamp in milliseconds
                if ts > 1e11:
                    ts /= 1000.0
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                return None
        if isinstance(val, str):
            val_str = val.strip()
            if not val_str:
                return None
            # Check for numeric timestamp in string form
            try:
                num = float(val_str)
                if num > 1e11:
                    num /= 1000.0
                return datetime.fromtimestamp(num, tz=timezone.utc)
            except ValueError:
                pass
            # Try ISO format
            try:
                iso_str = val_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                pass
            # Try common RFC / HTTP date formats
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S",
                "%d %b %Y %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(val_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _detect_experience_level(
        title: str,
        description: str = "",
        employment_type: Optional[str] = None,
    ) -> Optional[str]:
        """Infer experience level from title, description, or employment type."""
        t_lower = title.lower()
        d_lower = description.lower()[:500] if description else ""
        emp_lower = (employment_type or "").lower()

        if "intern" in t_lower or "internship" in t_lower or "intern" in emp_lower:
            return "Internship"
        if (
            "fresher" in t_lower
            or "fresh graduate" in t_lower
            or "0-1 year" in t_lower
            or "0-1 yrs" in t_lower
        ):
            return "Fresher"
        if any(
            kw in t_lower
            for kw in [
                "entry level", "entry-level", "junior", "trainee",
                "apprentice", "graduate engineer", "associate software",
            ]
        ):
            return "Entry-level"

        # Explicitly tag senior/lead/management roles as Experienced so they don't leak through
        if any(
            kw in t_lower
            for kw in [
                "senior", "sr.", "sr ", "lead", "principal", "staff", "architect",
                "director", "manager", "head of", "vp", "vice president",
            ]
        ) and not any(kw in t_lower for kw in ["intern", "trainee", "junior"]):
            return "Experienced"

        if "intern" in d_lower or "internship" in d_lower:
            return "Internship"
        if "fresher" in d_lower:
            return "Fresher"
        if any(kw in d_lower for kw in ["entry level", "entry-level", "0-1 year", "no experience"]):
            return "Entry-level"

        return None

    def _validate_and_build_job(self, **kwargs: Any) -> Optional[RawJob]:
        """Safely validate fields and instantiate a RawJob model."""
        try:
            # Fallback description to title if empty
            if not kwargs.get("description"):
                kwargs["description"] = kwargs.get("title", "")
            # Ensure valid application URL
            app_url = (kwargs.get("application_url") or "").strip()
            if not app_url.startswith(("http://", "https://")):
                self.logger.debug("invalid_application_url", url=app_url)
                return None
            kwargs["application_url"] = app_url

            # Ensure company and title are non-empty
            company = (kwargs.get("company") or "").strip()
            if not company:
                return None
            kwargs["company"] = company

            title = (kwargs.get("title") or "").strip()
            if not title:
                return None
            kwargs["title"] = title

            job = RawJob(**kwargs)
            self.stats["fetched"] += 1
            return job
        except ValidationError as e:
            self.logger.warning("job_validation_failed", error=str(e), title=kwargs.get("title"))
            self.stats["errors"] += 1
            return None
        except Exception as e:
            self.logger.error("job_creation_unexpected_error", error=str(e))
            self.stats["errors"] += 1
            return None
