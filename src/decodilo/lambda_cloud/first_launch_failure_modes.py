"""Failure-mode table for future Lambda first-launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaFirstLaunchFailureMode(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode_id: str
    description: str
    detection: str
    mitigation: str
    required_evidence: list[str] = Field(default_factory=list)
    manual_review_trigger: str
    residual_risk: str


class LambdaFirstLaunchFailureModeTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    failure_modes: list[LambdaFirstLaunchFailureMode]
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_launch_failure_mode_table() -> LambdaFirstLaunchFailureModeTable:
    definitions = [
        (
            "launch_response_lost",
            "Launch request succeeds but response is lost.",
            "Read-only list/get shows a ledger-correlated owned instance.",
            "Use idempotency key and ledger reconciliation before any retry.",
        ),
        (
            "launch_timeout_instance_exists",
            "Launch request times out but the instance exists.",
            "Read-only discovery finds a matching pending or running owned instance.",
            "Treat as launched until termination verification completes.",
        ),
        (
            "launch_response_malformed",
            "Launch response is malformed.",
            "Parser rejects response while request audit records an attempted future mutation.",
            "Block retry until read-only reconciliation resolves ownership.",
        ),
        (
            "instance_stuck_pending",
            "Instance remains pending beyond the launch window.",
            "Read-only status polling exceeds deadline.",
            "Trigger termination safety review and manual operator escalation.",
        ),
        (
            "running_health_unknown",
            "Instance is running but health is unknown.",
            "Read-only state is running while local health evidence is absent.",
            "Do not run workload; execute reviewed teardown path.",
        ),
        (
            "terminate_response_lost",
            "Terminate request succeeds but response is lost.",
            "Read-only verification reports absent or terminal state.",
            "Continue verification; do not retry blindly without idempotency.",
        ),
        (
            "terminate_timeout",
            "Terminate request times out.",
            "Read-only verification remains non-terminal by deadline.",
            "Escalate manual review and keep ledger marked non-terminal.",
        ),
        (
            "termination_state_unknown",
            "Termination state is unknown.",
            "List/get endpoint cannot confirm absent or terminal state.",
            "Manual review required; OS shutdown is insufficient.",
        ),
        (
            "verification_endpoint_unavailable",
            "List/get endpoint is unavailable during verification.",
            "Read-only endpoint returns unavailable or rate limit beyond retry policy.",
            "Pause lifecycle and escalate without additional mutation.",
        ),
        (
            "budget_threshold_exceeded",
            "Budget threshold is exceeded.",
            "Budget guard detects projected or elapsed spend beyond limit.",
            "Stop workload plans and execute reviewed termination path.",
        ),
        (
            "local_process_crash_after_launch",
            "Local process crashes after launch.",
            "Journal replay shows launch attempt without verified termination.",
            "Recover from journal and reconcile read-only state before continuing.",
        ),
        (
            "ledger_corrupted",
            "Resource ledger is corrupted.",
            "Hash validation or schema validation fails.",
            "Block mutation and require manual evidence reconstruction.",
        ),
        (
            "approval_manifest_mismatch",
            "Approval manifest hash does not match the armed plan.",
            "Arming gate hash check fails.",
            "Reject launch review until approval is reissued.",
        ),
        (
            "wrong_instance_type",
            "Requested instance type differs from approved shape.",
            "Plan/approval comparison fails.",
            "Block launch review.",
        ),
        (
            "wrong_region",
            "Requested region differs from approved region.",
            "Plan/approval comparison fails.",
            "Block launch review.",
        ),
        (
            "duplicate_launch_request",
            "Duplicate launch request is submitted.",
            "Idempotency key collision detected in journal.",
            "Return existing ledger-owned resource; do not create another.",
        ),
        (
            "duplicate_terminate_request",
            "Duplicate terminate request is submitted.",
            "Idempotency key collision detected in journal.",
            "Treat terminal state as success and keep verifying read-only state.",
        ),
    ]
    modes = [
        LambdaFirstLaunchFailureMode(
            mode_id=mode_id,
            description=description,
            detection=detection,
            mitigation=mitigation,
            required_evidence=["journal", "resource_ledger", "read_only_audit"],
            manual_review_trigger="state remains ambiguous or non-terminal after deadline",
            residual_risk="requires human review because M023 does not implement real mutation",
        )
        for mode_id, description, detection, mitigation in definitions
    ]
    return LambdaFirstLaunchFailureModeTable(failure_modes=modes)


def load_lambda_first_launch_failure_mode_table(
    path: str | Path,
) -> LambdaFirstLaunchFailureModeTable:
    return LambdaFirstLaunchFailureModeTable.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_launch_failure_mode_table(
    path: str | Path,
    table: LambdaFirstLaunchFailureModeTable,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(table.to_json(), encoding="utf-8")
