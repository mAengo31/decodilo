"""Strand-compatible response-loss control check for future lower-cost review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.strand_cli_request_shapes import validate_strand_launch_payload
from decodilo.lambda_cloud.strand_cli_response_shapes import (
    parse_strand_error_message,
    parse_strand_launch_instance_id,
    parse_strand_terminate_success,
)


class LambdaStrandResponseLossControlCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    timeout_seconds: float
    response_capture_active: bool
    status_before_parse: bool
    capture_redacted_headers: bool
    capture_content_type: bool
    capture_body_size: bool
    body_sample_enabled: bool = False
    no_auto_launch_retry: bool
    strand_launch_parser_accepts_data_instance_ids: bool
    strand_terminate_empty_2xx_supported: bool
    strand_error_parser_accepts_error_message: bool
    strand_launch_payload_shape_valid: bool
    setup_or_cloud_init_fields_absent: bool
    controls_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaStrandResponseLossControlCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("response-loss controls cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_strand_response_loss_control_check(
    *,
    timeout_seconds: float = 30.0,
    response_capture_active: bool = True,
    status_before_parse: bool = True,
    capture_redacted_headers: bool = True,
    capture_content_type: bool = True,
    capture_body_size: bool = True,
    body_sample_enabled: bool = False,
    no_auto_launch_retry: bool = True,
    include_setup_field_in_fixture: bool = False,
) -> LambdaStrandResponseLossControlCheck:
    blockers: list[str] = []
    if timeout_seconds < 30.0:
        blockers.append("timeout_seconds_below_30")
    if not response_capture_active:
        blockers.append("response_capture_not_active")
    if not status_before_parse:
        blockers.append("status_before_parse_not_enabled")
    if not capture_redacted_headers:
        blockers.append("redacted_headers_not_captured")
    if not capture_content_type:
        blockers.append("content_type_not_captured")
    if not capture_body_size:
        blockers.append("body_size_not_captured")
    if body_sample_enabled:
        blockers.append("body_samples_must_remain_disabled_for_m037r")
    if not no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    launch_parser_ok = _parser_accepts_launch_response()
    terminate_ok = parse_strand_terminate_success(status_code=204, payload=None)
    error_parser_ok = parse_strand_error_message({"error": {"message": "bad request"}}) == (
        "bad request"
    )
    payload_ok = _payload_is_valid(include_setup_field_in_fixture)
    setup_absent = not include_setup_field_in_fixture
    if not launch_parser_ok:
        blockers.append("strand_launch_response_parser_does_not_accept_data_instance_ids")
    if not terminate_ok:
        blockers.append("strand_terminate_empty_2xx_not_supported")
    if not error_parser_ok:
        blockers.append("strand_error_parser_does_not_accept_error_message")
    if not payload_ok:
        blockers.append("strand_launch_payload_shape_invalid")
    if not setup_absent:
        blockers.append("setup_cloud_init_or_user_data_field_present")
    return LambdaStrandResponseLossControlCheck(
        timeout_seconds=timeout_seconds,
        response_capture_active=response_capture_active,
        status_before_parse=status_before_parse,
        capture_redacted_headers=capture_redacted_headers,
        capture_content_type=capture_content_type,
        capture_body_size=capture_body_size,
        body_sample_enabled=body_sample_enabled,
        no_auto_launch_retry=no_auto_launch_retry,
        strand_launch_parser_accepts_data_instance_ids=launch_parser_ok,
        strand_terminate_empty_2xx_supported=terminate_ok,
        strand_error_parser_accepts_error_message=error_parser_ok,
        strand_launch_payload_shape_valid=payload_ok,
        setup_or_cloud_init_fields_absent=setup_absent,
        controls_passed=not blockers,
        blockers=blockers,
        warnings=[
            "Strand response-loss controls are offline compatibility checks only",
            "future launch review still requires operator approval",
        ],
    )


def _parser_accepts_launch_response() -> bool:
    return parse_strand_launch_instance_id({"data": {"instance_ids": ["i-test"]}}) == "i-test"


def _payload_is_valid(include_setup_field: bool) -> bool:
    payload: dict[str, object] = {
        "region_name": "us-west-1",
        "instance_type_name": "gpu_1x_h100_pcie",
        "ssh_key_names": ["existing-key"],
        "quantity": 1,
    }
    if include_setup_field:
        payload["cloud_init"] = "# forbidden"
    try:
        validate_strand_launch_payload(payload)
    except Exception:  # noqa: BLE001
        return False
    return True


def load_lambda_strand_response_loss_control_check(
    path: str | Path,
) -> LambdaStrandResponseLossControlCheck:
    return LambdaStrandResponseLossControlCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_strand_response_loss_control_check(
    path: str | Path,
    report: LambdaStrandResponseLossControlCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
