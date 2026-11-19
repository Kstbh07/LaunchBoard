"""Unit tests for SmartRecruiters collector."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.collectors.smartrecruiters_collector import SmartRecruitersCollector


@pytest.mark.asyncio
async def test_smartrecruiters_collector_initialization():
    collector = SmartRecruitersCollector()
    assert collector.name == "smartrecruiters"
    assert "swiggy" in collector.companies
    assert "freshworks" in collector.companies


@pytest.mark.asyncio
async def test_smartrecruiters_collect_mock():
    collector = SmartRecruitersCollector(companies=["swiggy"])

    sample_postings = {
        "content": [
            {
                "id": "sr-101",
                "name": "Software Development Engineer - I",
                "location": {
                    "city": "Bengaluru",
                    "region": "Karnataka",
                    "country": "in",
                    "fullLocation": "Bengaluru, Karnataka, India",
                    "remote": False,
                },
                "typeOfEmployment": {"label": "Full-time"},
                "experienceLevel": {"label": "Entry-level"},
                "releasedDate": "2026-11-15T10:00:00Z",
            },
            {
                "id": "sr-102",
                "name": "Frontend Intern",
                "location": {
                    "city": "Bengaluru",
                    "country": "in",
                    "fullLocation": "Bengaluru, India",
                },
                "typeOfEmployment": {"label": "Internship"},
                "releasedDate": "2026-11-16T12:00:00Z",
            },
            {
                "id": "sr-103",
                "name": "US Account Manager",
                "location": {
                    "city": "San Francisco",
                    "country": "us",
                    "fullLocation": "San Francisco, CA, USA",
                },
            },
        ],
        "totalFound": 3,
    }

    sample_detail = {
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "text": "<p>Work on Swiggy delivery engine with <b>Python</b>.</p>"
                },
                "qualifications": {
                    "text": "<p>B.Tech in Computer Science.</p>"
                },
            }
        }
    }

    mock_client = AsyncMock()

    def mock_get(url):
        res = MagicMock()
        res.status_code = 200
        if "postings?" in url:
            res.json.return_value = sample_postings
        else:
            res.json.return_value = sample_detail
        return res

    mock_client.get = AsyncMock(side_effect=mock_get)
    collector.client = mock_client

    jobs = await collector.collect()

    # Expect 2 India jobs, US job filtered out
    assert len(jobs) == 2
    assert jobs[0].company == "Swiggy"
    assert jobs[0].title == "Software Development Engineer - I"
    assert "Bengaluru" in jobs[0].location
    assert jobs[0].employment_type == "Full-time"
    assert jobs[0].experience_level == "Entry-level"
    assert "Python" in jobs[0].description

    assert jobs[1].title == "Frontend Intern"
    assert jobs[1].employment_type == "Internship"
    assert jobs[1].experience_level == "Internship"
