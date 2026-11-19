"""RSS and Atom Feed Collector.

Fetches job listings from various public RSS/Atom feeds without authentication:
- Indeed India RSS feeds for fresher, internship, and entry-level jobs
- Public remote tech boards (Remotive, Jobicy, WeWorkRemotely)
Extracts company names from structured entry metadata or title naming conventions.
"""
import asyncio
from datetime import datetime, timezone
import re
from typing import Any, Optional

import feedparser
import httpx

from app.collectors.base import BaseCollector
from app.schemas.collector import RawJob


class RssCollector(BaseCollector):
    """Collector for RSS/Atom job feeds."""

    name: str = "rss"
    rate_limit_delay: float = 1.0

    DEFAULT_FEEDS: dict[str, str] = {
        "Jobicy Remote": "https://jobicy.com/?feed=job_feed",
        "WeWorkRemotely Programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "WeWorkRemotely DevOps": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "WeWorkRemotely Design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
        "WeWorkRemotely Product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
        "WeWorkRemotely Support": "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    }

    def __init__(self, feeds: Optional[dict[str, str]] = None) -> None:
        super().__init__()
        self.feeds = feeds or self.DEFAULT_FEEDS

    async def collect(self) -> list[RawJob]:
        """Collect and parse jobs from all configured RSS/Atom feeds."""
        all_jobs: list[RawJob] = []
        seen_urls: set[str] = set()

        for idx, (feed_name, feed_url) in enumerate(self.feeds.items()):
            if idx > 0:
                await asyncio.sleep(self.rate_limit_delay)

            self.logger.info("fetching_rss_feed", feed=feed_name, url=feed_url)
            try:
                response = await self.client.get(feed_url)
                if response.status_code != 200:
                    self.logger.warning(
                        "rss_fetch_failed",
                        feed=feed_name,
                        status_code=response.status_code,
                    )
                    continue

                feed_data = feedparser.parse(response.text)
                if feed_data.bozo and not feed_data.entries:
                    self.logger.warning(
                        "rss_parse_error",
                        feed=feed_name,
                        error=str(feed_data.bozo_exception),
                    )
                    continue

                for entry in feed_data.entries:
                    link = (entry.get("link") or "").strip()
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    job = self._parse_entry(entry, feed_name)
                    if job:
                        all_jobs.append(job)

            except httpx.HTTPError as exc:
                self.logger.error("rss_network_error", feed=feed_name, error=str(exc))
                self.errors.append(f"Network error for {feed_name}: {exc}")
            except Exception as exc:
                self.logger.error("rss_process_error", feed=feed_name, error=str(exc))
                self.errors.append(f"Process error for {feed_name}: {exc}")

        filtered = self._filter_fresher_india(all_jobs)
        self.logger.info("rss_filtering_done", total=len(all_jobs), filtered=len(filtered))
        return filtered

    def _parse_entry(self, entry: Any, feed_name: str) -> Optional[RawJob]:
        """Parse an RSS feed entry into a RawJob."""
        raw_title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not raw_title or not link:
            return None

        # Extract title and company from common RSS title formats
        title, company = self._extract_title_and_company(raw_title, entry, feed_name)
        if not title or not company:
            return None

        # Description
        raw_desc = ""
        if entry.get("summary"):
            raw_desc = entry.get("summary")
        elif entry.get("description"):
            raw_desc = entry.get("description")
        elif entry.get("content"):
            contents = entry.get("content")
            if isinstance(contents, list) and contents:
                raw_desc = contents[0].get("value", "")

        description = self._clean_html(raw_desc) or title

        # Publication date
        posted_at: Optional[datetime] = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                posted_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                posted_at = None
        if not posted_at:
            posted_at = self._parse_datetime(entry.get("published") or entry.get("updated"))

        # Tags / skills
        skills: list[str] = []
        tags = entry.get("tags", [])
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict) and t.get("term"):
                    skills.append(str(t["term"]).strip())
                elif isinstance(t, str):
                    skills.append(t.strip())

        # Experience level detection
        exp_level = self._detect_experience_level(
            title=title,
            description=description,
        )

        # Location heuristic
        location = "India" if "India" in feed_name else None
        is_remote = "remote" in raw_title.lower() or "remote" in description.lower()

        return self._validate_and_build_job(
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=None,
            experience_level=exp_level,
            application_url=link,
            source_name=f"RSS:{feed_name}",
            source_url=link,
            source_job_id=entry.get("id") or link,
            posted_at=posted_at,
            is_remote=is_remote,
            skills=skills,
        )

    def _extract_title_and_company(
        self,
        raw_title: str,
        entry: Any,
        feed_name: str,
    ) -> tuple[str, str]:
        """Extract clean title and company name from feed item."""
        # 1. Check entry metadata for author or source publisher
        author = (entry.get("author") or entry.get("author_name") or "").strip()
        if author:
            return raw_title, author

        # 2. Check title separators: "Company: Title" or "Title at Company" or "Title @ Company"
        # "Title at Company"
        match = re.search(r"^(.*?)\s+at\s+(.+)$", raw_title, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # "Title @ Company"
        match = re.search(r"^(.*?)\s*@\s*(.+)$", raw_title)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # "Company: Title"
        match = re.search(r"^([^:]+):\s*(.+)$", raw_title)
        if match:
            return match.group(2).strip(), match.group(1).strip()

        # "Title - Company" or "Company - Title"
        if " - " in raw_title:
            parts = raw_title.split(" - ", 1)
            # Typically first part might be company or title; if feed is Indeed, format is: "Job Title - Company Name"
            if "Indeed" in feed_name:
                return parts[0].strip(), parts[1].strip()
            return parts[0].strip(), parts[1].strip()

        # "Title | Company"
        if " | " in raw_title:
            parts = raw_title.split(" | ", 1)
            return parts[0].strip(), parts[1].strip()

        # Fallback to feed name
        return raw_title, feed_name
