"""Review-only lockfile for a future first Lambda launch plan."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator


class LambdaLaunchDryRunLockfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    lockfile_schema_version: int = 1
    run_id: str
    launch_plan_hash: str
    teardown_plan_hash: str
    budget_lock_hash: str
    approval_hash: str
    operation_spec_hash: str
    termination_runbook_hash: str
    launch_window_policy_hash: str
    created_at_utc: str | None = None
    expires_at_utc: str | None = None
    locked_for_review_only: bool = True
    executable: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaLaunchDryRunLockfile:
        if not self.locked_for_review_only or self.executable:
            raise ValueError("M025 lockfile must be review-only and non-executable")
        if self.launch_ready or self.launch_allowed or self.real_mutation_enabled:
            raise ValueError("M025 lockfile cannot enable launch or mutation")
        if self.expires_at_utc is not None:
            expires = datetime.fromisoformat(self.expires_at_utc.replace("Z", "+00:00"))
            if expires < datetime.now(UTC):
                raise ValueError("M025 lockfile is expired")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_dry_run_lockfile(
    *,
    run_id: str,
    launch_plan_hash: str,
    teardown_plan_hash: str,
    budget_lock_hash: str,
    approval_hash: str,
    operation_spec_hash: str,
    termination_runbook_hash: str,
    launch_window_policy_hash: str,
    expires_at_utc: str | None = None,
) -> LambdaLaunchDryRunLockfile:
    return LambdaLaunchDryRunLockfile(
        run_id=run_id,
        launch_plan_hash=launch_plan_hash,
        teardown_plan_hash=teardown_plan_hash,
        budget_lock_hash=budget_lock_hash,
        approval_hash=approval_hash,
        operation_spec_hash=operation_spec_hash,
        termination_runbook_hash=termination_runbook_hash,
        launch_window_policy_hash=launch_window_policy_hash,
        expires_at_utc=expires_at_utc,
    )


def load_lambda_launch_dry_run_lockfile(path: str | Path) -> LambdaLaunchDryRunLockfile:
    return LambdaLaunchDryRunLockfile.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_launch_dry_run_lockfile(
    path: str | Path,
    lockfile: LambdaLaunchDryRunLockfile,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lockfile.to_json(), encoding="utf-8")
