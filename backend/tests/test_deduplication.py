"""Tests for the deduplication engine."""
import pytest
from app.services.deduplication import (
    normalize_company,
    normalize_title,
    normalize_location,
    normalize_url,
    generate_fingerprint,
    is_fuzzy_duplicate,
    is_url_duplicate,
)


class TestNormalizeCompany:
    def test_basic(self):
        assert normalize_company("Google") == "google"

    def test_removes_suffix(self):
        assert normalize_company("TCS Pvt. Ltd.") == "tcs"
        assert normalize_company("Infosys Limited") == "infosys"
        assert normalize_company("Wipro Technologies") == "wipro"

    def test_removes_special_chars(self):
        assert normalize_company("Tech@Corp!") == "techcorp"

    def test_strips_whitespace(self):
        assert normalize_company("  Google  ") == "google"

    def test_removes_india_suffix(self):
        assert normalize_company("Microsoft India") == "microsoft"
        assert normalize_company("Amazon (India)") == "amazon"


class TestNormalizeTitle:
    def test_basic(self):
        assert normalize_title("Software Engineer") == "software engineer"

    def test_removes_location_suffix(self):
        result = normalize_title("SDE - Remote")
        assert "remote" not in result

    def test_removes_city_suffix(self):
        result = normalize_title("Backend Developer - Bengaluru")
        assert "bengaluru" not in result

    def test_strips_special_chars(self):
        result = normalize_title("SDE-II (Backend)")
        assert result == "sdeii backend"


class TestNormalizeLocation:
    def test_bangalore_to_bengaluru(self):
        assert "bengaluru" in normalize_location("Bangalore")

    def test_gurgaon_to_gurugram(self):
        assert "gurugram" in normalize_location("Gurgaon")

    def test_bombay_to_mumbai(self):
        assert "mumbai" in normalize_location("Bombay")

    def test_delhi_ncr(self):
        assert "delhi" in normalize_location("Delhi NCR")
        assert "delhi" in normalize_location("NCR")

    def test_none_returns_unknown(self):
        assert normalize_location(None) == "unknown"

    def test_empty_returns_unknown(self):
        assert normalize_location("") == "unknown"


class TestNormalizeUrl:
    def test_removes_protocol(self):
        result = normalize_url("https://www.example.com/jobs/123")
        assert not result.startswith("http")
        assert "example.com/jobs/123" in result

    def test_removes_www(self):
        result = normalize_url("https://www.example.com")
        assert not result.startswith("www.")

    def test_removes_trailing_slash(self):
        result = normalize_url("https://example.com/jobs/")
        assert not result.endswith("/")

    def test_removes_utm_params(self):
        result = normalize_url("https://example.com/jobs/123?utm_source=google&utm_medium=cpc")
        assert "utm_" not in result


class TestGenerateFingerprint:
    def test_deterministic(self):
        fp1 = generate_fingerprint("Google", "SDE Intern", "Bengaluru")
        fp2 = generate_fingerprint("Google", "SDE Intern", "Bengaluru")
        assert fp1 == fp2

    def test_case_insensitive(self):
        fp1 = generate_fingerprint("Google", "SDE Intern", "Bengaluru")
        fp2 = generate_fingerprint("GOOGLE", "sde intern", "BENGALURU")
        assert fp1 == fp2

    def test_normalizes_company_suffix(self):
        fp1 = generate_fingerprint("TCS", "Developer", "Mumbai")
        fp2 = generate_fingerprint("TCS Pvt. Ltd.", "Developer", "Mumbai")
        assert fp1 == fp2

    def test_normalizes_city(self):
        fp1 = generate_fingerprint("Google", "SDE", "Bangalore")
        fp2 = generate_fingerprint("Google", "SDE", "Bengaluru")
        assert fp1 == fp2

    def test_different_jobs_different_fp(self):
        fp1 = generate_fingerprint("Google", "SDE Intern", "Bengaluru")
        fp2 = generate_fingerprint("Microsoft", "SDE Intern", "Bengaluru")
        assert fp1 != fp2

    def test_is_64_chars_hex(self):
        fp = generate_fingerprint("Test", "Job", "City")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


class TestFuzzyDuplicate:
    def test_exact_match(self):
        assert is_fuzzy_duplicate(
            "Software Engineer", "Google",
            "Software Engineer", "Google"
        )

    def test_similar_titles(self):
        assert is_fuzzy_duplicate(
            "Software Development Engineer", "Google",
            "Software Dev Engineer", "Google"
        )

    def test_different_company(self):
        assert not is_fuzzy_duplicate(
            "Software Engineer", "Google",
            "Software Engineer", "Microsoft"
        )

    def test_different_roles(self):
        assert not is_fuzzy_duplicate(
            "Frontend Developer", "Google",
            "Backend Developer", "Google"
        )


class TestUrlDuplicate:
    def test_same_url(self):
        assert is_url_duplicate(
            "https://example.com/jobs/123",
            "https://example.com/jobs/123"
        )

    def test_www_difference(self):
        assert is_url_duplicate(
            "https://www.example.com/jobs/123",
            "https://example.com/jobs/123"
        )

    def test_trailing_slash(self):
        assert is_url_duplicate(
            "https://example.com/jobs/123/",
            "https://example.com/jobs/123"
        )

    def test_different_urls(self):
        assert not is_url_duplicate(
            "https://example.com/jobs/123",
            "https://example.com/jobs/456"
        )
