"""LLM Classification Engine for LaunchBoard.

Supports Gemini and OpenAI APIs for job classification.
Returns structured JSON validated with Pydantic.
"""
import json
from pathlib import Path
import re
import time
from typing import Any, Optional, Tuple

import google.generativeai as genai
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.schemas.classification import ClassificationResult

logger = structlog.get_logger()

VALID_ROLE_CATEGORIES = [
    "Software Development",
    "Frontend Development",
    "Backend Development",
    "Full Stack Development",
    "AI/ML Engineering",
    "Data Science",
    "Data Analytics",
    "DevOps / Cloud",
    "Cybersecurity",
    "Mobile Development",
    "QA / Testing",
    "UI/UX Design",
    "Product Management",
    "Business Development",
    "Other",
]

VALID_EXPERIENCE_LEVELS = ["Fresher", "Internship", "Entry-level", "Experienced", "Unknown"]
VALID_EMPLOYMENT_TYPES = ["Internship", "Full-time", "Part-time", "Contract"]


def _clean_json_str(text: str) -> str:
    """Strip markdown code fence blocks if returned by the LLM."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


class ClassificationService:
    """Service for classifying job listings using Google Gemini or OpenAI LLMs."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model_name = settings.AI_MODEL
        self.provider = settings.AI_PROVIDER.lower()
        self.confidence_high = settings.CLASSIFICATION_CONFIDENCE_HIGH
        self.confidence_medium = settings.CLASSIFICATION_CONFIDENCE_MEDIUM
        self.openai_client: Any = None
        self.model: Any = None
        self.available: bool = False

        # Load prompt template from prompts directory or fallback
        prompt_path = (
            Path(__file__).parent.parent.parent.parent
            / "prompts"
            / "job_classification.txt"
        )
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")
        else:
            self.prompt_template = self._default_prompt()

        # Configure provider API
        if self.provider == "gemini":
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Map retired/deprecated Gemini models to currently active generation models
                if self.model_name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"):
                    self.model_name = "gemini-flash-lite-latest"
                self.model = genai.GenerativeModel(self.model_name)
                self.available = True
            else:
                self.available = False
                logger.warning("classification_unavailable", reason="No GEMINI_API_KEY configured")
        elif self.provider == "openai":
            if settings.OPENAI_API_KEY:
                try:
                    from openai import AsyncOpenAI

                    self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    self.available = True
                except ImportError:
                    self.available = False
                    logger.warning(
                        "classification_unavailable",
                        reason="openai library not installed",
                    )
            else:
                self.available = False
                logger.warning("classification_unavailable", reason="No OPENAI_API_KEY configured")
        else:
            self.available = False
            logger.warning("classification_unavailable", reason=f"Unsupported provider: {self.provider}")

    def _default_prompt(self) -> str:
        """Comprehensive fallback prompt if prompts/job_classification.txt is not found."""
        return """You are an expert job classifier for the Indian job market. Analyze the following job listing and return a structured JSON classification.

Job Title: {title}
Company: {company}
Location: {location}
Job Description:
{description}

Classify this job and return ONLY a valid JSON object with these fields:

1. "role_category": Exactly one of:
   - "Software Development"
   - "Frontend Development"
   - "Backend Development"
   - "Full Stack Development"
   - "AI/ML Engineering"
   - "Data Science"
   - "Data Analytics"
   - "DevOps / Cloud"
   - "Cybersecurity"
   - "Mobile Development"
   - "QA / Testing"
   - "UI/UX Design"
   - "Product Management"
   - "Business Development"
   - "Other"

2. "city": The normalized Indian city name (e.g., "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai"). Use "Remote" if fully remote. Use "Unknown" if the city cannot be determined. Do NOT invent a city.

3. "skills": Array of specific technical skills mentioned (e.g., ["Python", "Django", "PostgreSQL"]). Extract only skills explicitly mentioned. Do not infer unmentioned skills.

4. "experience_level": Exactly one of:
   - "Fresher" — Explicitly for candidates with 0 years of experience or fresh graduates
   - "Internship" — Explicitly an internship program, usually time-bound (2-6 months)
   - "Entry-level" — For 0-2 years of experience, or open to freshers but not explicitly stated
   - "Experienced" — Requires 2+ years of experience or specific professional background
   - "Unknown" — Cannot be determined from the description

5. "employment_type": Exactly one of:
   - "Internship" — Time-bound learning/training program
   - "Full-time" — Permanent full-time employment
   - "Part-time" — Part-time employment
   - "Contract" — Fixed-term contract

6. "is_remote": Boolean. true only if the job is fully remote or work-from-home. Hybrid roles should be false.

7. "confidence": Float between 0.0 and 1.0 indicating your confidence in this classification.

Classification guidelines:
- Infer the role from actual responsibilities and required skills, not just the job title
- Security roles: Any security-focused roles (e.g., "Software Engineer, Security", "Application Security", "Security Analyst", "Infosec") MUST be classified as "Cybersecurity", NOT generic "Backend Development" or "Software Development".
- A "Software Engineer" who builds APIs is "Backend Development", not generic "Software Development"
- A role requiring both frontend and backend is "Full Stack Development"
- Product/project management roles go to "Product Management"
- Normalize Indian city names: "Bangalore" → "Bengaluru", "Gurgaon" → "Gurugram"
- Missing city: If the job is located in a non-Indian city (e.g. London, San Francisco, New York, Berlin, Singapore) or the city is not specified, city MUST be "Unknown". Never invent an Indian city for non-Indian locations.
- Remote vs On-site:
  * Multilingual remote terms: Recognize German "Homeoffice", "100% Remote", "Telearbeit", French "Télétravail", Spanish "Teletrabajo" as fully remote (is_remote: true, city: "Remote").
  * Physical non-Indian office: If Location lists a specific non-Indian city without "remote" (e.g., "London", "Singapore", "New York"), is_remote MUST be false and city MUST be "Unknown", even if the company is remote-friendly.
- When the description mentions multiple cities, use the primary/first city
- If the job says "India" without a specific city, use "Unknown"

Return ONLY the JSON object, no additional text or markdown formatting.
"""

    async def classify_job(
        self,
        title: str,
        company: str,
        description: str,
        location: str | None = None,
    ) -> Tuple[Optional[ClassificationResult], dict[str, Any]]:
        """Classify a job listing using configured LLM provider.

        Args:
            title: Job title.
            company: Company name.
            description: Job description text.
            location: Optional location string.

        Returns:
            Tuple of (ClassificationResult or None, usage_stats dict)
            usage_stats contains: model_name, input_tokens, output_tokens, processing_time_ms
        """
        if not self.available:
            return None, {
                "model_name": self.model_name,
                "error": "API not configured",
                "input_tokens": 0,
                "output_tokens": 0,
                "processing_time_ms": 0,
            }

        start_time = time.time()
        # Truncate very long descriptions to avoid context window/cost issues
        prompt = self.prompt_template.format(
            title=title,
            company=company,
            description=description[:3000],
            location=location or "Not specified",
        )

        try:
            result_str, usage = await self._call_llm(prompt)
            processing_time = int((time.time() - start_time) * 1000)

            # Clean and validate JSON response
            cleaned_json = _clean_json_str(result_str)
            classification = ClassificationResult.model_validate_json(cleaned_json)

            # Normalize and enforce allowed categorical fields
            if classification.role_category not in VALID_ROLE_CATEGORIES:
                classification.role_category = "Other"
            if classification.experience_level not in VALID_EXPERIENCE_LEVELS:
                classification.experience_level = "Unknown"
            if classification.employment_type not in VALID_EMPLOYMENT_TYPES:
                classification.employment_type = "Full-time"

            usage_stats = {
                "model_name": self.model_name,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "processing_time_ms": processing_time,
            }

            return classification, usage_stats

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("classification_failed", error=str(e), title=title)
            return None, {
                "model_name": self.model_name,
                "error": str(e),
                "processing_time_ms": processing_time,
                "input_tokens": 0,
                "output_tokens": 0,
            }

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(min=4, max=25),
        retry=retry_if_exception_type((json.JSONDecodeError, ValueError, Exception)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> Tuple[str, dict[str, int]]:
        """Call the LLM API with retry logic and exponential backoff."""
        if self.provider == "gemini":
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text = response.text
            input_tokens = (
                response.usage_metadata.prompt_token_count
                if hasattr(response, "usage_metadata") and response.usage_metadata
                else 0
            )
            output_tokens = (
                response.usage_metadata.candidates_token_count
                if hasattr(response, "usage_metadata") and response.usage_metadata
                else 0
            )
            usage = {
                "input_tokens": input_tokens or 0,
                "output_tokens": output_tokens or 0,
            }
            # Validate JSON parseability
            json.loads(_clean_json_str(text))
            return text, usage

        elif self.provider == "openai":
            if not self.openai_client:
                raise ValueError("OpenAI client is not initialized")

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            choice = response.choices[0]
            text = choice.message.content or "{}"
            usage = {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            }
            json.loads(_clean_json_str(text))
            return text, usage

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_confidence_level(self, confidence: float) -> str:
        """Determine confidence category tier for workflow routing."""
        if confidence >= self.confidence_high:
            return "high"
        elif confidence >= self.confidence_medium:
            return "medium"
        return "low"
