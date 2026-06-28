"""Future-only M079R2 retry authorization after artifact capture policy fix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
    load_lambda_learner_syncer_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    load_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    load_lambda_remote_vslice_declared_artifact_policy,
)

LambdaM079R2NextSyntheticExperimentAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m079r2_next_synthetic_experiment_retry",
]


class LambdaM079R2NextSyntheticExperimentAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M079S"
    authorization_status: LambdaM079R2NextSyntheticExperimentAuthorizationStatus
    reason: str
    run_now: bool = False
    future_only: bool = True
    declared_artifact_path: str = LEARNER_SYNCER_DECLARED_ARTIFACT_PATH
    max_launch_attempts: int = 1
    max_instances: int = 1
    halt_after_first_failed_live_stage: bool = True
    no_internet_install: bool = True
    no_downloads: bool = True
    no_real_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(
        self,
    ) -> LambdaM079R2NextSyntheticExperimentAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M079R2 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M079S authorization cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m079r2_next_synthetic_experiment_retry"
            and self.blockers
        ):
            raise ValueError("authorized M079R2 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m079r2_next_synthetic_experiment_authorization_from_paths(
    *,
    attempt_closeout: str | Path,
    declared_artifact_policy: str | Path,
    previous_authorization: str | Path,
) -> LambdaM079R2NextSyntheticExperimentAuthorization:
    closeout = load_lambda_learner_syncer_smoke_attempt_closeout(attempt_closeout)
    policy = load_lambda_remote_vslice_declared_artifact_policy(declared_artifact_policy)
    previous = load_lambda_m079r_next_synthetic_experiment_authorization(
        previous_authorization
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m079r_attempt_closeout_not_succeeded")
    if (
        closeout.closeout_status
        != "closed_learner_syncer_smoke_command_passed_artifact_capture_blocked"
    ):
        blockers.append("m079r_closeout_status_not_retryable")
    if not closeout.learner_syncer_smoke_command_passed:
        blockers.append("learner_syncer_smoke_command_not_passed")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["declared_artifact_policy_not_defined"])
    if policy.declared_artifact_path != LEARNER_SYNCER_DECLARED_ARTIFACT_PATH:
        blockers.append("learner_syncer_declared_artifact_path_missing")
    if (
        previous.authorization_status
        != "authorized_for_future_m079r_next_synthetic_experiment"
    ):
        blockers.append("previous_m079r_authorization_not_valid")
    status: LambdaM079R2NextSyntheticExperimentAuthorizationStatus = (
        "authorized_for_future_m079r2_next_synthetic_experiment_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM079R2NextSyntheticExperimentAuthorization(
        authorization_status=status,
        reason=(
            "retry_with_manifest_declared_artifact_capture_fixed"
            if not blockers
            else "blocked"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only",
            "M079R2 still requires fresh discovery and supervised approval",
        ],
    )


def load_lambda_m079r2_next_synthetic_experiment_authorization(
    path: str | Path,
) -> LambdaM079R2NextSyntheticExperimentAuthorization:
    return LambdaM079R2NextSyntheticExperimentAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m079r2_next_synthetic_experiment_authorization(
    path: str | Path,
    authorization: LambdaM079R2NextSyntheticExperimentAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
