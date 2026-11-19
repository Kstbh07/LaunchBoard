"""LLM Cost Tracking Service.

Tracks token usage and calculates costs based on configurable pricing.
"""
from typing import Any, Dict

import structlog

logger = structlog.get_logger()

# Pricing configuration - update when model provider pricing changes
PRICING_CONFIG: dict[str, dict[str, Any]] = {
    "gemini-flash-lite-latest": {
        "input_per_1m_tokens": 0.075,
        "output_per_1m_tokens": 0.30,
        "source": "Google AI Studio pricing",
        "effective_date": "2026-01-01",
    },
    "gemini-2.0-flash": {
        "input_per_1m_tokens": 0.10,  # USD per 1M input tokens
        "output_per_1m_tokens": 0.40,  # USD per 1M output tokens
        "source": "Google AI Studio pricing",
        "effective_date": "2025-02-01",
    },
    "gemini-1.5-flash": {
        "input_per_1m_tokens": 0.075,
        "output_per_1m_tokens": 0.30,
        "source": "Google AI Studio pricing",
        "effective_date": "2025-01-01",
    },
    "gpt-4o-mini": {
        "input_per_1m_tokens": 0.15,
        "output_per_1m_tokens": 0.60,
        "source": "OpenAI pricing",
        "effective_date": "2025-01-01",
    },
}


class CostTracker:
    """Tracks token consumption and calculates running dollar costs."""

    def __init__(self, model_name: str = "gemini-2.0-flash") -> None:
        self.model_name = model_name
        self.pricing: dict[str, Any] = PRICING_CONFIG.get(
            model_name,
            PRICING_CONFIG["gemini-2.0-flash"],
        )
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_requests: int = 0

    def record_usage(self, input_tokens: int, output_tokens: int) -> float:
        """Record token usage from a single request and return estimated cost in USD.

        Args:
            input_tokens: Number of prompt/input tokens.
            output_tokens: Number of generated/output tokens.

        Returns:
            Cost of this request in USD (rounded to 6 decimal places).
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1

        cost = self.calculate_cost(input_tokens, output_tokens)
        logger.debug(
            "llm_usage_recorded",
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            total_requests=self.total_requests,
        )
        return cost

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD for given token counts."""
        input_cost = (input_tokens / 1_000_000.0) * self.pricing["input_per_1m_tokens"]
        output_cost = (output_tokens / 1_000_000.0) * self.pricing["output_per_1m_tokens"]
        return round(input_cost + output_cost, 6)

    def get_total_cost(self) -> float:
        """Return the cumulative cost in USD across all recorded requests."""
        return self.calculate_cost(self.total_input_tokens, self.total_output_tokens)

    def get_cost_per_job(self) -> float:
        """Return the average cost in USD per classified job."""
        if self.total_requests == 0:
            return 0.0
        return round(self.get_total_cost() / self.total_requests, 6)

    def get_cost_per_1000(self) -> float:
        """Return the projected cost in USD per 1,000 classified jobs."""
        return round(self.get_cost_per_job() * 1000.0, 4)

    def get_report(self) -> Dict[str, Any]:
        """Generate a complete telemetry report matching CostReport schema."""
        return {
            "model_name": self.model_name,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_requests": self.total_requests,
            "total_cost_usd": self.get_total_cost(),
            "avg_cost_per_job": self.get_cost_per_job(),
            "cost_per_1000_jobs": self.get_cost_per_1000(),
            "pricing_config": self.pricing,
            "note": "Costs are estimates based on published API pricing.",
        }

    def reset(self) -> None:
        """Reset usage metrics back to initial state."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
