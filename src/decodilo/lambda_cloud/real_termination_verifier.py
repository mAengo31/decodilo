"""Read-only termination verification for M029."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_mutation_transport import LambdaM029RealMutationTransport

TERMINAL_STATES = {"terminated", "terminating", "preempted", "absent"}


class LambdaM029TerminationVerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    owned_instance_id: str
    verification_passed: bool
    observed_state: str
    read_only_get_used: bool = False
    read_only_list_used: bool = False
    manual_review_required: bool = False
    os_shutdown_used: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def verify_m029_owned_instance_terminated(
    *,
    transport: LambdaM029RealMutationTransport,
    arming_token: LambdaM029ArmingToken,
    owned_instance_id: str,
    idempotency_key: str,
) -> LambdaM029TerminationVerificationReport:
    payload = transport.request_json(
        operation="get_instance",
        payload={"instance_id": owned_instance_id},
        instance_id=owned_instance_id,
        arming_token=arming_token,
        idempotency_key=idempotency_key,
    )
    state = "absent"
    if isinstance(payload.get("data"), dict):
        state = str(payload["data"].get("status") or "unknown")
    passed = state in TERMINAL_STATES
    return LambdaM029TerminationVerificationReport(
        owned_instance_id=owned_instance_id,
        verification_passed=passed,
        observed_state=state,
        read_only_get_used=True,
        manual_review_required=not passed,
        warnings=["OS shutdown is insufficient; Lambda read-only verification was used."],
    )


def write_lambda_m029_termination_verification_report(
    path: str | Path,
    report: LambdaM029TerminationVerificationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
