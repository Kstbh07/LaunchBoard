"""LaunchBoard collectors package."""
from typing import Optional, Sequence

from app.collectors.base import BaseCollector
from app.collectors.adzuna_collector import AdzunaCollector
from app.collectors.arbeitnow_collector import ArbeitnowCollector
from app.collectors.ashby_collector import AshbyCollector
from app.collectors.findwork_collector import FindworkCollector
from app.collectors.greenhouse_collector import GreenhouseCollector
from app.collectors.himalayas_collector import HimalayasCollector
from app.collectors.jobicy_collector import JobicyCollector
from app.collectors.lever_collector import LeverCollector
from app.collectors.remoteok_collector import RemoteokCollector
from app.collectors.remotive_collector import RemotiveCollector
from app.collectors.rss_collector import RssCollector
from app.collectors.smartrecruiters_collector import SmartRecruitersCollector


def get_all_collectors(sources: Optional[Sequence[str]] = None) -> list[BaseCollector]:
    """Get instances of all registered job collectors.

    Args:
        sources: Optional list of source names to filter by. If None, returns all collectors.

    Returns:
        List of initialized BaseCollector instances.
    """
    collectors: list[BaseCollector] = [
        AdzunaCollector(),
        ArbeitnowCollector(),
        AshbyCollector(),
        FindworkCollector(),
        GreenhouseCollector(),
        HimalayasCollector(),
        JobicyCollector(),
        LeverCollector(),
        RemoteokCollector(),
        RemotiveCollector(),
        RssCollector(),
        SmartRecruitersCollector(),
    ]
    if sources:
        sources_lower = {s.lower() for s in sources}
        return [c for c in collectors if c.name.lower() in sources_lower]
    return collectors


__all__ = [
    "BaseCollector",
    "AdzunaCollector",
    "ArbeitnowCollector",
    "AshbyCollector",
    "FindworkCollector",
    "GreenhouseCollector",
    "HimalayasCollector",
    "JobicyCollector",
    "LeverCollector",
    "RemoteokCollector",
    "RemotiveCollector",
    "RssCollector",
    "SmartRecruitersCollector",
    "get_all_collectors",
]
