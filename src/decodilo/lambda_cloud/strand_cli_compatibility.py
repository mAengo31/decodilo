"""Review-only compatibility model for Strand-AI lambda-cli behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.strand_cli_fixtures import (
    STRAND_API_BASE_URL,
    STRAND_AUTH_SCHEME,
    STRAND_CLI_REPO_URL,
    STRAND_DEFAULT_TIMEOUT_SECONDS,
    STRAND_GET_INSTANCE,
    STRAND_LAUNCH_ENDPOINT,
    STRAND_LAUNCH_METHOD,
    STRAND_LIST_INSTANCE_TYPES,
    STRAND_LIST_INSTANCES,
    STRAND_TERMINATE_ENDPOINT,
    STRAND_TERMINATE_METHOD,
)

StrandLambdaCLICompatibilityStatus = Literal[
    "compatible",
    "partially_compatible",
    "incompatible",
    "needs_migration",
]


class StrandLambdaCLICompatibilityProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_repo_url: str = STRAND_CLI_REPO_URL
    source_commit_or_version: str | None = None
    source_is_official: bool = False
    source_is_behavioral_evidence: bool = True
    api_base_url: str = STRAND_API_BASE_URL
    timeout_seconds: float = STRAND_DEFAULT_TIMEOUT_SECONDS
    auth_scheme: str = STRAND_AUTH_SCHEME
    endpoints: dict[str, dict[str, str]] = Field(default_factory=dict)
    request_shapes: dict[str, object] = Field(default_factory=dict)
    response_shapes: dict[str, object] = Field(default_factory=dict)
    terminate_semantics: str = "2xx status is success; response body is not required"
    error_semantics: str = "JSON error.message contains provider message"

    @model_validator(mode="after")
    def _validate_evidence_source(self) -> StrandLambdaCLICompatibilityProfile:
        if self.source_is_official:
            raise ValueError("Strand CLI profile must remain marked unofficial")
        if not self.source_is_behavioral_evidence:
            raise ValueError("Strand CLI profile must be behavioral evidence")
        return self


class StrandLambdaCLICompatibilityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    profile: StrandLambdaCLICompatibilityProfile
    compatibility_status: StrandLambdaCLICompatibilityStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> StrandLambdaCLICompatibilityReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("Strand compatibility report cannot enable launch")
        if self.compatibility_status == "compatible" and self.blockers:
            raise ValueError("compatible Strand report cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_strand_cli_compatibility_profile() -> StrandLambdaCLICompatibilityProfile:
    return StrandLambdaCLICompatibilityProfile(
        endpoints={
            "list_instance_types": {"method": "GET", "path": STRAND_LIST_INSTANCE_TYPES},
            "list_instances": {"method": "GET", "path": STRAND_LIST_INSTANCES},
            "get_instance": {"method": "GET", "path": STRAND_GET_INSTANCE},
            "launch_one_instance": {
                "method": STRAND_LAUNCH_METHOD,
                "path": STRAND_LAUNCH_ENDPOINT,
            },
            "terminate_owned_instance": {
                "method": STRAND_TERMINATE_METHOD,
                "path": STRAND_TERMINATE_ENDPOINT,
            },
        },
        request_shapes={
            "launch_one_instance": {
                "region_name": "<region>",
                "instance_type_name": "<gpu>",
                "ssh_key_names": ["<ssh_key>"],
                "quantity": 1,
                "name": "optional",
                "file_system_names": "optional",
            },
            "terminate_owned_instance": {"instance_ids": ["<owned_instance_id>"]},
        },
        response_shapes={
            "launch_one_instance": {"data": {"instance_ids": ["<id>"]}},
            "terminate_owned_instance": "2xx status success; body optional",
            "error": {"error": {"message": "..."}},
        },
    )


def build_strand_cli_compatibility_report() -> StrandLambdaCLICompatibilityReport:
    profile = build_strand_cli_compatibility_profile()
    return StrandLambdaCLICompatibilityReport(
        profile=profile,
        compatibility_status="compatible",
        warnings=[
            "Strand-AI lambda-cli is unofficial and not affiliated with Lambda",
            "Profile is behavioral evidence from an operator-tested implementation",
        ],
    )


def write_strand_cli_compatibility_report(
    path: str | Path,
    report: StrandLambdaCLICompatibilityReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_strand_cli_compatibility_report(
    path: str | Path,
) -> StrandLambdaCLICompatibilityReport:
    return StrandLambdaCLICompatibilityReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
