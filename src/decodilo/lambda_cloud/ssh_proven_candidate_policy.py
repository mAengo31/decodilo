"""Future-only candidate policy for SSH-proven remote vertical slices."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_readiness_history import (
    load_lambda_ssh_readiness_history,
)


class LambdaSSHProvenCandidatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy_status: str
    ssh_proven_candidate_regions: list[dict[str, str | int]] = Field(default_factory=list)
    excluded_candidate_regions: list[dict[str, str | int]] = Field(default_factory=list)
    preferred_known_good_candidate_region: dict[str, str] | None = None
    fresh_live_availability_required: bool = True
    silent_unproven_substitution_allowed: bool = False
    operator_approval_required_for_new_candidate: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHProvenCandidatePolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.silent_unproven_substitution_allowed
        ):
            raise ValueError("SSH-proven policy cannot enable launch or silent substitution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_proven_candidate_policy_from_path(
    *,
    history: str | Path,
) -> LambdaSSHProvenCandidatePolicy:
    readiness = load_lambda_ssh_readiness_history(history)
    proven = []
    excluded = []
    for summary in readiness.candidate_region_summaries:
        item = {
            "selected_candidate": summary.selected_candidate,
            "selected_region": summary.selected_region,
            "ssh_ready_success_count": summary.ssh_ready_success_count,
            "ssh_port_not_reachable_count": summary.ssh_port_not_reachable_count,
        }
        if summary.ssh_ready_success_count > 0 and summary.ssh_port_not_reachable_count == 0:
            proven.append(item)
        if summary.ssh_port_not_reachable_count > 0:
            excluded.append(item)
    return LambdaSSHProvenCandidatePolicy(
        policy_status="policy_defined",
        ssh_proven_candidate_regions=proven,
        excluded_candidate_regions=excluded,
        preferred_known_good_candidate_region=readiness.preferred_known_good_candidate_region,
        warnings=[
            "Fresh live availability alone must not override recent SSH-readiness failure",
            "Future Decodilo vertical slices must prefer SSH-proven candidate/region pairs",
        ],
    )


def load_lambda_ssh_proven_candidate_policy(
    path: str | Path,
) -> LambdaSSHProvenCandidatePolicy:
    return LambdaSSHProvenCandidatePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_proven_candidate_policy(
    path: str | Path,
    report: LambdaSSHProvenCandidatePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
