"""Read-only Lambda API retry policy."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RateLimitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=2, ge=1, le=5)
    retry_status_codes: set[int] = Field(default_factory=lambda: {429, 500, 502, 503, 504})
    base_delay_seconds: float = Field(default=0.0, ge=0)

    def should_retry(self, *, status_code: int, attempt: int) -> bool:
        if status_code in {401, 403}:
            return False
        return attempt < self.max_attempts and status_code in self.retry_status_codes
