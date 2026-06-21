"""Non-executable command preview for future M045 catalog rotation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_rotation_shape_authorization import (
    load_lambda_catalog_rotation_shape_authorization,
)

LambdaCatalogRotationCommandPreviewStatus = Literal[
    "ready_for_future_m045",
    "blocked",
]


class LambdaCatalogRotationCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaCatalogRotationCommandPreviewStatus
    executable: bool = False
    selected_candidate: str | None = None
    selected_ssh_key_hash: str | None = None
    workdir_placeholder: str = "/tmp/decodilo-lambda-m045"
    command_preview: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaCatalogRotationCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog-rotation command preview cannot be executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_rotation_command_preview_from_path(
    authorization: str | Path,
) -> LambdaCatalogRotationCommandPreview:
    auth = load_lambda_catalog_rotation_shape_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m045_catalog_rotation_launch_review"
        and not auth.blockers
    )
    return LambdaCatalogRotationCommandPreview(
        preview_status="ready_for_future_m045" if ready else "blocked",
        selected_candidate=auth.selected_candidate if ready else None,
        selected_ssh_key_hash=auth.selected_ssh_key_hash if ready else None,
        command_preview=_command_preview() if ready else [],
        blockers=[] if ready else auth.blockers or ["m045_authorization_not_ready"],
        warnings=[
            "command preview is non-executable",
            "raw SSH key names are not included in the preview",
        ],
    )


def _command_preview() -> list[str]:
    return [
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
        "--catalog-rotation-authorization",
        "/tmp/decodilo-lambda-m045-catalog-rotation-authorization.json",
        "--catalog-rotation-risk-acceptance",
        "/tmp/decodilo-lambda-catalog-rotation-risk-acceptance.json",
        "--catalog-rotation-cost-review",
        "/tmp/decodilo-lambda-catalog-rotation-cost-review.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--workdir",
        "/tmp/decodilo-lambda-m045",
        "--execute-real-launch",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
    ]


def load_lambda_catalog_rotation_command_preview(
    path: str | Path,
) -> LambdaCatalogRotationCommandPreview:
    return LambdaCatalogRotationCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_command_preview(
    path: str | Path,
    report: LambdaCatalogRotationCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
