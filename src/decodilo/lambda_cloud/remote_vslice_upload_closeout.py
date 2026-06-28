"""Close out M073R as a source-upload readiness failure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.upload_failure_classifier import (
    load_lambda_upload_failure_classification,
)

LambdaRemoteVSliceUploadCloseoutStatus = Literal[
    "closed_source_upload_ssh_banner_timeout",
    "closed_source_upload_connection_closed",
    "unresolved",
]


class LambdaRemoteVSliceUploadCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    closeout_status: LambdaRemoteVSliceUploadCloseoutStatus
    closeout_succeeded: bool
    source_bundle_uploaded: bool
    dependency_bundle_uploaded: bool
    tiny_smoke_attempted: bool
    decodilo_not_tested: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_closeout(self) -> LambdaRemoteVSliceUploadCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M073S closeout must not authorize launch or spend")
        if self.closeout_succeeded and self.closeout_status == "unresolved":
            raise ValueError("unresolved closeout cannot be marked succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_lambda_remote_vslice_upload_closeout_from_paths(
    *,
    classification: str | Path,
    post_discovery: str | Path,
) -> LambdaRemoteVSliceUploadCloseout:
    cls = load_lambda_upload_failure_classification(classification)
    post = _read_json(post_discovery)
    final_instance_count = post.get("instance_count")
    final_unmanaged_count = post.get("unmanaged_count")
    blockers: list[str] = list(cls.blockers)
    if not cls.termination_verified:
        blockers.append("termination_not_verified")
    if final_instance_count != 0:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count != 0:
        blockers.append("final_unmanaged_count_nonzero")
    if cls.decodilo_tested:
        blockers.append("decodilo_was_tested")
    if cls.tiny_smoke_attempted:
        blockers.append("tiny_smoke_was_attempted")

    if blockers:
        status: LambdaRemoteVSliceUploadCloseoutStatus = "unresolved"
    elif cls.failure_classification == "ssh_banner_exchange_timeout_during_upload":
        status = "closed_source_upload_ssh_banner_timeout"
    elif cls.failure_classification == "scp_connection_closed_during_upload":
        status = "closed_source_upload_connection_closed"
    else:
        status = "unresolved"
        blockers.append("unsupported_upload_failure_classification")

    return LambdaRemoteVSliceUploadCloseout(
        closeout_status=status,
        closeout_succeeded=not blockers,
        source_bundle_uploaded=cls.source_bundle_upload_verified,
        dependency_bundle_uploaded=cls.dependency_bundle_upload_attempted,
        tiny_smoke_attempted=cls.tiny_smoke_attempted,
        decodilo_not_tested=not cls.decodilo_tested,
        termination_verified=cls.termination_verified,
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        historical_billable_action_performed=cls.historical_billable_action_performed,
        blockers=blockers,
        warnings=[
            "M073S is offline; historical M073R billable action remains evidence only",
        ],
    )


def load_lambda_remote_vslice_upload_closeout(
    path: str | Path,
) -> LambdaRemoteVSliceUploadCloseout:
    return LambdaRemoteVSliceUploadCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_upload_closeout(
    path: str | Path,
    report: LambdaRemoteVSliceUploadCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
