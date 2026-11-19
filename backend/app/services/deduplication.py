"""Deduplication engine for LaunchBoard.

Uses multi-level matching:
1. Deterministic fingerprint (SHA256 of normalized company+title+location)
2. URL-based matching (normalized application URLs)
3. Fuzzy matching via rapidfuzz (title similarity + company similarity)
"""
import hashlib
import re
from typing import Optional, Sequence

from rapidfuzz import fuzz
import structlog

from app.schemas.collector import RawJob

logger = structlog.get_logger()


def normalize_company(name: str) -> str:
    """Normalize company name for comparison.

    Strips out standard corporate designations, legal suffixes, technology
    catch-alls, and punctuation to generate a canonical company root name.
    """
    if not name:
        return ""
    name = name.lower().strip()
    # Strip parenthesized (india) or similar tags first
    name = re.sub(r"\(india\)", "", name, flags=re.IGNORECASE)
    
    # Strip common legal and business suffixes using word boundaries
    suffixes = [
        r"pvt\.?\s*ltd\.?",
        r"private\s+limited",
        r"limited",
        r"ltd\.?",
        r"inc\.?",
        r"llc",
        r"llp",
        r"corporation",
        r"technologies",
        r"technology",
        r"solutions",
        r"services",
        r"consulting",
        r"software",
        r"systems",
        r"labs",
        r"group",
        r"india",
    ]
    for pattern in suffixes:
        name = re.sub(r"\b" + pattern + r"\b", "", name, flags=re.IGNORECASE)

        
    # Remove special chars, extra whitespace
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name



def normalize_title(title: str) -> str:
    """Normalize job title for comparison.

    Removes common regional markers, remote tags, and punctuation noise.
    """
    if not title:
        return ""
    title = title.lower().strip()
    # Remove common noise
    for noise in [
        "- remote", "(remote)", "- india", "(india)",
        "- bengaluru", "- mumbai", "- delhi", "- pune", "- hyderabad",
        "- chennai", "- kolkata", "- noida", "- gurgaon", "- gurugram"
    ]:
        title = title.replace(noise, "")
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def normalize_location(location: str | None) -> str:
    """Normalize location for comparison.

    Maps alternate Indian city spellings to canonical names and extracts
    the primary city name when multi-city or composite strings are encountered.
    """
    if not location:
        return "unknown"
    location = location.lower().strip()
    # Map alternate names
    mapping = {
        "bangalore": "bengaluru",
        "gurgaon": "gurugram",
        "bombay": "mumbai",
        "madras": "chennai",
        "calcutta": "kolkata",
        "trivandrum": "thiruvananthapuram",
        "new delhi": "delhi",
        "ncr": "delhi",
        "delhi ncr": "delhi",
        "delhi/ncr": "delhi",
        "mangalore": "mangaluru",
        "mysore": "mysuru",
        "allahabad": "prayagraj",
        "pondicherry": "puducherry",
    }
    for old, new in mapping.items():
        if old in location:
            location = location.replace(old, new)
    # Extract first city if multiple
    location = re.sub(r"[^a-z\s]", "", location).strip()
    parts = location.split()
    if parts:
        return parts[0] if len(parts) == 1 else location
    return "unknown"


def normalize_url(url: str) -> str:
    """Normalize URL for comparison.

    Strips protocols, trailing slashes, and standard UTM/tracking parameters.
    """
    if not url:
        return ""
    url = url.lower().strip()
    url = re.sub(r"^https?://(www\.)?", "", url)
    url = url.rstrip("/")
    # Remove tracking params
    url = re.sub(r"[?&](utm_\w+|ref|source|campaign)=[^&]*", "", url)
    return url


def generate_fingerprint(company: str, title: str, location: str | None = None) -> str:
    """Generate deterministic fingerprint from normalized fields."""
    norm_company = normalize_company(company)
    norm_title = normalize_title(title)
    norm_location = normalize_location(location)
    content = f"{norm_company}|{norm_title}|{norm_location}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_fuzzy_duplicate(
    job1_title: str,
    job1_company: str,
    job2_title: str,
    job2_company: str,
    threshold: float = 85.0,
) -> bool:
    """Check if two jobs are fuzzy duplicates.

    Both title and company similarity must meet or exceed the threshold.
    Uses maximum of token_sort_ratio and token_set_ratio for title comparison.
    """
    t1 = normalize_title(job1_title)
    t2 = normalize_title(job2_title)
    title_sim = max(fuzz.token_sort_ratio(t1, t2), fuzz.token_set_ratio(t1, t2))
    
    c1 = normalize_company(job1_company)
    c2 = normalize_company(job2_company)
    company_sim = max(fuzz.token_sort_ratio(c1, c2), fuzz.token_set_ratio(c1, c2))
    return title_sim >= threshold and company_sim >= threshold



def is_url_duplicate(url1: str, url2: str) -> bool:
    """Check if two application URLs point to the same job."""
    return normalize_url(url1) == normalize_url(url2)


class DeduplicationService:
    """Deduplication engine managing multi-stage deduplication pipeline.

    Multi-level matching pipeline:
    1. Deterministic fingerprint (SHA256 of normalized company+title+location)
    2. URL-based matching (normalized application URLs)
    3. Fuzzy matching via rapidfuzz (title similarity + company similarity)
    """

    def __init__(self, fuzzy_threshold: float = 85.0) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self.stats = {
            "total_processed": 0,
            "new": 0,
            "updated": 0,
            "duplicates": 0,
        }

    def process(
        self,
        jobs: list[RawJob],
        existing_fingerprints: set[str] | Sequence[str],
        existing_urls: Optional[set[str] | Sequence[str]] = None,
    ) -> tuple[list[RawJob], list[RawJob], int]:
        """Process incoming raw jobs against existing database fingerprints and URLs.

        Args:
            jobs: List of incoming RawJob objects from collectors.
            existing_fingerprints: Set or sequence of known fingerprints already in database.
            existing_urls: Optional set or sequence of application URLs already in database.

        Returns:
            Tuple of (new_jobs, updated_jobs, duplicate_count)
        """
        new_jobs: list[RawJob] = []
        updated_jobs: list[RawJob] = []
        duplicate_count = 0

        db_fps: set[str] = set(existing_fingerprints)
        db_urls: set[str] = {normalize_url(u) for u in existing_urls} if existing_urls else set()

        seen_batch_fps: set[str] = set()
        seen_batch_urls: set[str] = set()
        accepted_candidates: list[RawJob] = []

        for job in jobs:
            self.stats["total_processed"] += 1
            fp = generate_fingerprint(job.company, job.title, job.location)
            norm_url = normalize_url(job.application_url)

            # Stage 1: Deterministic Fingerprint Matching
            if fp in db_fps:
                if fp in seen_batch_fps:
                    duplicate_count += 1
                    logger.debug(
                        "duplicate_skipped_intra_batch_reseen",
                        company=job.company,
                        title=job.title,
                        fingerprint=fp,
                    )
                else:
                    updated_jobs.append(job)
                    seen_batch_fps.add(fp)
                    if norm_url:
                        seen_batch_urls.add(norm_url)
                    self.stats["updated"] += 1
                    logger.debug(
                        "job_marked_for_update",
                        company=job.company,
                        title=job.title,
                        fingerprint=fp,
                    )
                continue

            if fp in seen_batch_fps:
                duplicate_count += 1
                logger.debug(
                    "duplicate_job_fingerprint",
                    company=job.company,
                    title=job.title,
                    fingerprint=fp,
                )
                continue

            # Stage 2: URL-based Matching
            if norm_url and norm_url in db_urls:
                duplicate_count += 1
                logger.info(
                    "duplicate_job_db_url",
                    company=job.company,
                    title=job.title,
                    url=job.application_url,
                )
                continue

            if norm_url and norm_url in seen_batch_urls:
                duplicate_count += 1
                logger.info(
                    "duplicate_job_batch_url",
                    company=job.company,
                    title=job.title,
                    url=job.application_url,
                )
                continue

            # Stage 3: Fuzzy Matching against candidates accepted in this batch
            is_fuzzy = False
            for candidate in accepted_candidates:
                if is_fuzzy_duplicate(
                    job.title,
                    job.company,
                    candidate.title,
                    candidate.company,
                    threshold=self.fuzzy_threshold,
                ):
                    is_fuzzy = True
                    duplicate_count += 1
                    logger.info(
                        "duplicate_job_fuzzy",
                        candidate_title=job.title,
                        candidate_company=job.company,
                        matched_title=candidate.title,
                        matched_company=candidate.company,
                    )
                    break

            if is_fuzzy:
                continue

            # Job is verified unique
            new_jobs.append(job)
            accepted_candidates.append(job)
            seen_batch_fps.add(fp)
            if norm_url:
                seen_batch_urls.add(norm_url)
            self.stats["new"] += 1
            logger.debug(
                "new_job_accepted",
                company=job.company,
                title=job.title,
                fingerprint=fp,
            )

        self.stats["duplicates"] += duplicate_count
        logger.info(
            "deduplication_completed",
            total_processed=len(jobs),
            new=len(new_jobs),
            updated=len(updated_jobs),
            duplicates=duplicate_count,
        )

        return new_jobs, updated_jobs, duplicate_count

    def get_stats(self) -> dict[str, int]:
        """Return cumulative deduplication statistics."""
        return dict(self.stats)

    def reset_stats(self) -> None:
        """Reset deduplication statistics counters."""
        self.stats = {
            "total_processed": 0,
            "new": 0,
            "updated": 0,
            "duplicates": 0,
        }
