"""Non-executable runbook preview for future M079R2 retry."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    load_lambda_m079r2_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    load_lambda_remote_vslice_declared_artifact_policy,
)


class LambdaM079R2NextSyntheticExperimentRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M079S"
    preview_status: str
    executable: bool = False
    authorization_status: str
    declared_artifact_path: str | None
    capture_declared_artifact_on_success_or_failure: bool
    no_arbitrary_file_reads: bool
    no_training: bool = True
    no_downloads: bool = True
    runbook_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM079R2NextSyntheticExperimentRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("M079R2 preview must remain non-executable")
        if self.billable_action_performed:
            raise ValueError("M079S preview cannot spend money")
        if self.preview_status != "blocked" and self.blockers:
            raise ValueError("ready M079R2 preview cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m079r2_next_synthetic_experiment_runbook_preview_from_paths(
    *,
    authorization: str | Path,
    declared_artifact_policy: str | Path,
) -> LambdaM079R2NextSyntheticExperimentRunbookPreview:
    auth = load_lambda_m079r2_next_synthetic_experiment_authorization(authorization)
    policy = load_lambda_remote_vslice_declared_artifact_policy(declared_artifact_policy)
    blockers: list[str] = []
    if (
        auth.authorization_status
        != "authorized_for_future_m079r2_next_synthetic_experiment_retry"
    ):
        blockers.append("m079r2_authorization_not_valid")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["declared_artifact_policy_not_defined"])
    ready = not blockers
    return LambdaM079R2NextSyntheticExperimentRunbookPreview(
        preview_status=(
            "ready_for_future_m079r2_next_synthetic_experiment_retry_review"
            if ready
            else "blocked"
        ),
        authorization_status=auth.authorization_status,
        declared_artifact_path=policy.declared_artifact_path,
        capture_declared_artifact_on_success_or_failure=(
            policy.capture_on_success and policy.capture_on_failure
        ),
        no_arbitrary_file_reads=policy.no_arbitrary_file_reads,
        runbook_steps=[
            "fresh read-only discovery",
            "one launch only after explicit operator confirmation",
            "wait for TCP/22 and SSH banner readiness before upload",
            "upload source and dependency bundles once",
            "install dependencies from local wheelhouse only",
            "run the exact learner-syncer-smoke command once",
            (
                "capture only the manifest-declared learner/syncer artifact metadata "
                "and safe body or parsed summary on success or failure"
            ),
            "terminate owned instance and verify clean discovery",
        ],
        blockers=sorted(set(blockers)),
        warnings=["preview is non-executable and future-only"],
    )


def load_lambda_m079r2_next_synthetic_experiment_runbook_preview(
    path: str | Path,
) -> LambdaM079R2NextSyntheticExperimentRunbookPreview:
    return LambdaM079R2NextSyntheticExperimentRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m079r2_next_synthetic_experiment_runbook_preview(
    path: str | Path,
    preview: LambdaM079R2NextSyntheticExperimentRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(preview.to_json(), encoding="utf-8")
