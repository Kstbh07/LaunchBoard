"""Tests for collector schema and RawJob validation."""
import pytest
from pydantic import ValidationError
from app.schemas.collector import RawJob


class TestRawJobValidation:
    def test_valid_job(self):
        job = RawJob(
            title="Software Engineer Intern",
            company="Google",
            description="Work on exciting projects",
            location="Bengaluru",
            application_url="https://careers.google.com/jobs/123",
            source_name="Greenhouse:google",
        )
        assert job.title == "Software Engineer Intern"
        assert job.company == "Google"
        assert job.is_remote is False

    def test_empty_title_fails(self):
        with pytest.raises(ValidationError):
            RawJob(
                title="",
                company="Google",
                description="Test",
                application_url="https://example.com",
                source_name="test",
            )

    def test_whitespace_title_fails(self):
        with pytest.raises(ValidationError):
            RawJob(
                title="   ",
                company="Google",
                description="Test",
                application_url="https://example.com",
                source_name="test",
            )

    def test_empty_company_fails(self):
        with pytest.raises(ValidationError):
            RawJob(
                title="SDE",
                company="",
                description="Test",
                application_url="https://example.com",
                source_name="test",
            )

    def test_invalid_url_fails(self):
        with pytest.raises(ValidationError):
            RawJob(
                title="SDE",
                company="Google",
                description="Test",
                application_url="not-a-url",
                source_name="test",
            )

    def test_ftp_url_fails(self):
        with pytest.raises(ValidationError):
            RawJob(
                title="SDE",
                company="Google",
                description="Test",
                application_url="ftp://example.com/jobs",
                source_name="test",
            )

    def test_optional_fields(self):
        job = RawJob(
            title="SDE",
            company="Google",
            description="Test",
            application_url="https://example.com",
            source_name="test",
        )
        assert job.location is None
        assert job.employment_type is None
        assert job.experience_level is None
        assert job.source_url is None
        assert job.source_job_id is None
        assert job.posted_at is None
        assert job.skills == []

    def test_title_strips_whitespace(self):
        job = RawJob(
            title="  Software Engineer  ",
            company="  Google  ",
            description="Test",
            application_url="https://example.com",
            source_name="test",
        )
        assert job.title == "Software Engineer"
        assert job.company == "Google"

    def test_remote_flag(self):
        job = RawJob(
            title="SDE",
            company="Google",
            description="Test",
            application_url="https://example.com",
            source_name="test",
            is_remote=True,
        )
        assert job.is_remote is True

    def test_with_skills(self):
        job = RawJob(
            title="SDE",
            company="Google",
            description="Test",
            application_url="https://example.com",
            source_name="test",
            skills=["Python", "Django"],
        )
        assert job.skills == ["Python", "Django"]

    def test_new_collectors_registration(self):
        from app.collectors import get_all_collectors
        collectors = get_all_collectors()
        names = {c.name for c in collectors}
        assert "ashby" in names
        assert "jobicy" in names
        assert "remoteok" in names
        assert "greenhouse" in names
        assert "lever" in names
        assert "smartrecruiters" in names

    def test_scheduler_status_structure(self):
        from app.services.scheduler import CollectionScheduler
        sched = CollectionScheduler(interval_seconds=1800)
        status = sched.get_status()
        assert status["interval_seconds"] == 1800
        assert status["interval_minutes"] == 30
        assert "is_running" in status
        assert "total_scheduled_runs" in status
        assert status["total_scheduled_runs"] == 0

    def test_expiry_service_instantiation(self):
        from app.services.expiry import ExpiryService
        service = ExpiryService(db=None, expiry_days=45)
        assert service.expiry_days == 45

