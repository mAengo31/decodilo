"""Compare DecoDiLo's Lambda mutation surface with Strand CLI behavior."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
    prepare_minimal_launch_request,
    prepare_minimal_terminate_request,
)
from decodilo.lambda_cloud.real_mutation_transport import LambdaM029TransportConfig
from decodilo.lambda_cloud.strand_cli_fixtures import (
    STRAND_API_BASE_URL,
    STRAND_DEFAULT_TIMEOUT_SECONDS,
    STRAND_LAUNCH_ENDPOINT,
    STRAND_LAUNCH_METHOD,
    STRAND_TERMINATE_ENDPOINT,
    STRAND_TERMINATE_METHOD,
)
from decodilo.lambda_cloud.strand_cli_request_shapes import (
    build_strand_launch_payload,
    build_strand_terminate_payload,
    validate_strand_launch_payload,
    validate_strand_terminate_payload,
)
from decodilo.lambda_cloud.strand_cli_response_shapes import (
    parse_strand_launch_instance_id,
    parse_strand_terminate_success,
)


class StrandCLIGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    area: str
    severity: str
    expected: str
    observed: str
    migration_required: bool


class StrandCLIGapAnalysisReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gaps: list[StrandCLIGap] = Field(default_factory=list)
    migration_required: bool
    launch_blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> StrandCLIGapAnalysisReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("Strand gap analysis cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_strand_cli_gap_analysis() -> StrandCLIGapAnalysisReport:
    gaps: list[StrandCLIGap] = []
    warnings = [
        "Strand CLI is unofficial behavioral evidence; it is not Lambda support evidence"
    ]
    config = LambdaM029TransportConfig(
        base_url="memory://strand-compatibility",
        fake_server_mode=True,
    )
    _compare(
        gaps,
        "api_base_url",
        STRAND_API_BASE_URL,
        LambdaM029TransportConfig(
            base_url=STRAND_API_BASE_URL,
            allow_real_lambda_api=True,
        ).base_url,
        migration_required=False,
    )
    _compare(
        gaps,
        "timeout",
        str(STRAND_DEFAULT_TIMEOUT_SECONDS),
        str(config.timeout_seconds),
        migration_required=True,
    )
    launch = prepare_minimal_launch_request(
        LambdaMinimalLaunchOneInstanceRequest(
            instance_type="gpu_1x_h100_pcie",
            region="us-west-1",
            ssh_key_ref="existing-ssh-key",
            idempotency_key="idem",
            dry_run_plan_hash="plan",
            budget_lock_hash="budget",
            approval_manifest_hash="approval",
            resource_ledger_hash="ledger",
            teardown_plan_hash="teardown",
        )
    )
    terminate = prepare_minimal_terminate_request(
        LambdaMinimalTerminateOwnedInstanceRequest(
            owned_instance_id="fake-i-123",
            idempotency_key="idem",
            resource_scope_hash="scope",
            ledger_hash="ledger",
            termination_verification_policy_hash="term",
        )
    )
    _compare(gaps, "launch_method", STRAND_LAUNCH_METHOD, launch.future_http_method)
    _compare(
        gaps,
        "launch_endpoint",
        STRAND_LAUNCH_ENDPOINT,
        launch.future_endpoint_template,
    )
    _compare(
        gaps,
        "terminate_method",
        STRAND_TERMINATE_METHOD,
        terminate.future_http_method,
    )
    _compare(
        gaps,
        "terminate_endpoint",
        STRAND_TERMINATE_ENDPOINT,
        terminate.future_endpoint_template,
    )
    _validate_request_shapes(gaps)
    _validate_response_shapes(gaps)
    blockers = [
        f"strand_gap:{gap.area}"
        for gap in gaps
        if gap.migration_required or gap.severity == "blocker"
    ]
    return StrandCLIGapAnalysisReport(
        gaps=gaps,
        migration_required=bool(blockers),
        launch_blockers=blockers,
        warnings=warnings,
    )


def _compare(
    gaps: list[StrandCLIGap],
    area: str,
    expected: str,
    observed: str,
    *,
    migration_required: bool = True,
) -> None:
    if expected != observed:
        gaps.append(
            StrandCLIGap(
                area=area,
                severity="blocker",
                expected=expected,
                observed=observed,
                migration_required=migration_required,
            )
        )


def _validate_request_shapes(gaps: list[StrandCLIGap]) -> None:
    try:
        validate_strand_launch_payload(
            build_strand_launch_payload(
                region_name="us-west-1",
                instance_type_name="gpu_1x_h100_pcie",
                ssh_key_name="existing-ssh-key",
            )
        )
    except Exception as exc:  # noqa: BLE001
        gaps.append(
            StrandCLIGap(
                area="launch_payload_shape",
                severity="blocker",
                expected="valid Strand launch payload",
                observed=type(exc).__name__,
                migration_required=True,
            )
        )
    try:
        validate_strand_terminate_payload(build_strand_terminate_payload("i-123"))
    except Exception as exc:  # noqa: BLE001
        gaps.append(
            StrandCLIGap(
                area="terminate_payload_shape",
                severity="blocker",
                expected="valid Strand terminate payload",
                observed=type(exc).__name__,
                migration_required=True,
            )
        )


def _validate_response_shapes(gaps: list[StrandCLIGap]) -> None:
    try:
        parse_strand_launch_instance_id({"data": {"instance_ids": ["i-123"]}})
    except Exception as exc:  # noqa: BLE001
        gaps.append(
            StrandCLIGap(
                area="launch_response_parser",
                severity="blocker",
                expected="data.instance_ids[0]",
                observed=type(exc).__name__,
                migration_required=True,
            )
        )
    if not parse_strand_terminate_success(status_code=204, payload=None):
        gaps.append(
            StrandCLIGap(
                area="terminate_empty_2xx",
                severity="blocker",
                expected="2xx empty body accepted",
                observed="not accepted",
                migration_required=True,
            )
        )


def write_strand_cli_gap_analysis(path: str | Path, report: StrandCLIGapAnalysisReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_strand_cli_gap_analysis(path: str | Path) -> StrandCLIGapAnalysisReport:
    return StrandCLIGapAnalysisReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
