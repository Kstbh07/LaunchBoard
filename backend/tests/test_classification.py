"""Tests for classification schema validation and cost tracking."""
import pytest
import json
from pydantic import ValidationError
from app.schemas.classification import ClassificationResult
from app.services.cost_tracker import CostTracker


class TestClassificationResult:
    def test_valid_classification(self):
        data = {
            "role_category": "Backend Development",
            "city": "Bengaluru",
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience_level": "Fresher",
            "employment_type": "Full-time",
            "is_remote": False,
            "confidence": 0.92,
        }
        result = ClassificationResult(**data)
        assert result.role_category == "Backend Development"
        assert result.confidence == 0.92
        assert len(result.skills) == 3

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                role_category="Other",
                city="Unknown",
                skills=[],
                experience_level="Unknown",
                employment_type="Full-time",
                is_remote=False,
                confidence=1.5,  # Invalid: > 1.0
            )

    def test_negative_confidence(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                role_category="Other",
                city="Unknown",
                skills=[],
                experience_level="Unknown",
                employment_type="Full-time",
                is_remote=False,
                confidence=-0.1,  # Invalid: < 0.0
            )

    def test_from_json(self):
        json_str = json.dumps({
            "role_category": "Frontend Development",
            "city": "Mumbai",
            "skills": ["React", "TypeScript"],
            "experience_level": "Internship",
            "employment_type": "Internship",
            "is_remote": False,
            "confidence": 0.88,
        })
        result = ClassificationResult.model_validate_json(json_str)
        assert result.role_category == "Frontend Development"
        assert result.employment_type == "Internship"

    def test_defaults(self):
        data = {
            "role_category": "Other",
            "experience_level": "Unknown",
            "employment_type": "Full-time",
            "confidence": 0.5,
        }
        result = ClassificationResult(**data)
        assert result.city == "Unknown"
        assert result.skills == []
        assert result.is_remote is False

    def test_all_experience_levels(self):
        for level in ["Fresher", "Internship", "Entry-level", "Experienced", "Unknown"]:
            result = ClassificationResult(
                role_category="Other",
                experience_level=level,
                employment_type="Full-time",
                confidence=0.5,
            )
            assert result.experience_level == level


class TestCostTracker:
    def test_initial_state(self):
        tracker = CostTracker("gemini-2.0-flash")
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_requests == 0
        assert tracker.get_total_cost() == 0.0

    def test_record_usage(self):
        tracker = CostTracker("gemini-2.0-flash")
        cost = tracker.record_usage(1000, 200)
        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 200
        assert tracker.total_requests == 1
        assert cost > 0

    def test_cost_calculation(self):
        tracker = CostTracker("gemini-2.0-flash")
        # Gemini 2.0 Flash: $0.10 per 1M input, $0.40 per 1M output
        cost = tracker.calculate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(0.50, abs=0.01)  # $0.10 + $0.40

    def test_cost_per_job(self):
        tracker = CostTracker("gemini-2.0-flash")
        tracker.record_usage(500, 100)
        tracker.record_usage(600, 150)
        assert tracker.total_requests == 2
        cost_per_job = tracker.get_cost_per_job()
        assert cost_per_job > 0
        assert cost_per_job == tracker.get_total_cost() / 2

    def test_cost_per_1000(self):
        tracker = CostTracker("gemini-2.0-flash")
        tracker.record_usage(500, 100)
        cost_per_1000 = tracker.get_cost_per_1000()
        assert cost_per_1000 == pytest.approx(tracker.get_cost_per_job() * 1000)



    def test_report_format(self):
        tracker = CostTracker("gemini-2.0-flash")
        tracker.record_usage(1000, 200)
        report = tracker.get_report()
        assert "model_name" in report
        assert "total_input_tokens" in report
        assert "total_output_tokens" in report
        assert "total_cost_usd" in report
        assert "avg_cost_per_job" in report
        assert "cost_per_1000_jobs" in report
        assert "pricing_config" in report
        assert "note" in report
        assert report["model_name"] == "gemini-2.0-flash"

    def test_unknown_model_uses_default_pricing(self):
        tracker = CostTracker("unknown-model")
        # Should fall back to gemini-2.0-flash pricing
        cost = tracker.calculate_cost(1_000_000, 1_000_000)
        assert cost > 0
