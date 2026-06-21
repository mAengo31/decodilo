"""Launch correlation evidence for M029 response-loss handling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaM029LaunchCorrelationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    idempotency_key_hash: str
    request_hash: str
    planned_shape: str
    planned_region: str
    planned_image: str | None = None
    sent_at_utc: str | None = None
    provider_metadata_correlation_supported: bool = False
    limitations: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_launch_correlation_record(
    *,
    run_id: str,
    idempotency_key: str,
    planned_shape: str,
    planned_region: str,
    planned_image: str | None = None,
    sent_at_utc: str | None = None,
) -> LambdaM029LaunchCorrelationRecord:
    request_payload = {
        "run_id": run_id,
        "planned_shape": planned_shape,
        "planned_region": planned_region,
        "planned_image": planned_image,
    }
    return LambdaM029LaunchCorrelationRecord(
        run_id=run_id,
        idempotency_key_hash=hashlib.sha256(idempotency_key.encode()).hexdigest(),
        request_hash=hashlib.sha256(
            json.dumps(request_payload, sort_keys=True).encode()
        ).hexdigest(),
        planned_shape=planned_shape,
        planned_region=planned_region,
        planned_image=planned_image,
        sent_at_utc=sent_at_utc,
        limitations=["provider-visible request metadata correlation is not confirmed"],
    )


def write_lambda_m029_launch_correlation_record(
    path: str | Path,
    record: LambdaM029LaunchCorrelationRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
