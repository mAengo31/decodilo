"""M028 launch window lock for future M029 attempt."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaLaunchWindowPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_runtime_minutes: int = Field(default=30, gt=0)
    operator_required: bool = True
    background_execution_allowed: bool = False
    auto_retry_allowed: bool = False
    max_launch_attempts: int = 1
    max_terminate_attempts: int = 2


class LambdaLaunchWindowLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_window_id: str = "lambda-launch-window-lock-m028"
    valid_after_utc: str | None = None
    valid_until_utc: str | None = None
    policy: LambdaLaunchWindowPolicy = Field(default_factory=LambdaLaunchWindowPolicy)
    lock_hash: str
    locked_for_m029_authorization_only: bool = True
    launch_window_valid: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_window(self) -> LambdaLaunchWindowLock:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 launch window lock cannot enable launch or mutation")
        if self.policy.background_execution_allowed:
            raise ValueError("background execution is forbidden")
        if self.policy.max_launch_attempts != 1:
            raise ValueError("M029 authorization may permit only one launch attempt")
        if self.valid_until_utc is not None and _parse_utc(
            self.valid_until_utc
        ) <= datetime.now(timezone.utc):
            raise ValueError("launch window lock is expired")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_window_lock(
    *,
    max_runtime_minutes: int = 30,
    valid_after_utc: str | None = None,
    valid_until_utc: str | None = None,
) -> LambdaLaunchWindowLock:
    policy = LambdaLaunchWindowPolicy(max_runtime_minutes=max_runtime_minutes)
    material = "|".join([str(max_runtime_minutes), str(valid_after_utc), str(valid_until_utc)])
    blockers: list[str] = []
    if max_runtime_minutes > 30:
        blockers.append("runtime exceeds 30 minutes")
    return LambdaLaunchWindowLock(
        valid_after_utc=valid_after_utc,
        valid_until_utc=valid_until_utc,
        policy=policy,
        lock_hash=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        launch_window_valid=not blockers,
        blockers=blockers,
        warnings=["Launch window lock is M029 authorization evidence only."],
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_lambda_launch_window_lock(path: str | Path) -> LambdaLaunchWindowLock:
    return LambdaLaunchWindowLock.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_launch_window_lock(path: str | Path, lock: LambdaLaunchWindowLock) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lock.to_json(), encoding="utf-8")
