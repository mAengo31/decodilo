"""Non-executable command preview for future M042 catalog-availability launch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_availability_gate_check import (
    LambdaCatalogAvailabilityGateCheck,
    load_lambda_catalog_availability_gate_check,
)
from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    LambdaCatalogAvailabilityM042Authorization,
    load_lambda_catalog_availability_m042_authorization,
)

LambdaCatalogAvailabilityCommandPreviewStatus = Literal[
    "ready_for_future_m042",
    "blocked",
]


class LambdaCatalogAvailabilityCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaCatalogAvailabilityCommandPreviewStatus
    executable: bool = False
    selected_shape: str | None = None
    selected_ssh_key_hash: str | None = None
    command: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaCatalogAvailabilityCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M042 command preview must remain non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_availability_command_preview(
    *,
    m042_authorization: LambdaCatalogAvailabilityM042Authorization,
    gate_check: LambdaCatalogAvailabilityGateCheck,
) -> LambdaCatalogAvailabilityCommandPreview:
    blockers = sorted(set([*m042_authorization.blockers, *gate_check.blockers]))
    ready = (
        m042_authorization.authorization_status
        == "authorized_for_future_m042_catalog_availability_launch_review"
        and gate_check.gate_passed
        and not blockers
    )
    command = [
        "python",
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--env-file",
        ".env",
        "--env-key",
        "LAMBDA_API_KEY",
        "--m042-authorization",
        "/tmp/decodilo-lambda-m042-authorization.json",
        "--availability-first-plan",
        "/tmp/decodilo-lambda-availability-first-plan.json",
        "--catalog-availability-risk-acceptance",
        "/tmp/decodilo-lambda-catalog-availability-risk-acceptance.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--workdir",
        "/tmp/decodilo-lambda-m042",
        "--execute-real-launch",
        "<future-M042-operator-confirmation-required>",
    ]
    return LambdaCatalogAvailabilityCommandPreview(
        preview_status="ready_for_future_m042" if ready else "blocked",
        selected_shape=m042_authorization.selected_candidate,
        selected_ssh_key_hash=m042_authorization.selected_ssh_key_hash,
        command=command,
        blockers=blockers,
        warnings=[
            "command preview is non-executable in M041",
            "M042 must re-run gates and collect fresh operator confirmation",
        ],
    )


def build_lambda_catalog_availability_command_preview_from_paths(
    *,
    m042_authorization: str | Path,
    gate_check: str | Path,
) -> LambdaCatalogAvailabilityCommandPreview:
    return build_lambda_catalog_availability_command_preview(
        m042_authorization=load_lambda_catalog_availability_m042_authorization(
            m042_authorization
        ),
        gate_check=load_lambda_catalog_availability_gate_check(gate_check),
    )


def load_lambda_catalog_availability_command_preview(
    path: str | Path,
) -> LambdaCatalogAvailabilityCommandPreview:
    return LambdaCatalogAvailabilityCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_availability_command_preview(
    path: str | Path,
    report: LambdaCatalogAvailabilityCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
