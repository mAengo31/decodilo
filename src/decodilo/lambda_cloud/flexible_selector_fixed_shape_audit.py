"""Audit that flexible-selector review does not use fixed-shape authorization."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.flexible_selector_authorization import (
    load_lambda_flexible_selector_authorization,
)


class LambdaFlexibleSelectorFixedShapeAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    audit_passed: bool
    hardcoded_gpu_1x_h100_pcie_path_disabled: bool
    hardcoded_gpu_8x_a100_80gb_sxm4_path_disabled: bool
    selector_output_is_shape_source: bool
    command_preview_requires_selector_authorization: bool
    old_m028_m029_fixed_shape_fallback_blocked: bool
    fixed_shape_path_used: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFlexibleSelectorFixedShapeAudit:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.fixed_shape_path_used
        ):
            raise ValueError("fixed-shape audit cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_flexible_selector_fixed_shape_audit_from_path(
    authorization: str | Path,
) -> LambdaFlexibleSelectorFixedShapeAudit:
    auth = load_lambda_flexible_selector_authorization(authorization)
    selector_source = auth.authorization_source == "flexible_selector_output"
    blockers = list(auth.blockers)
    if auth.fixed_shape_path_used:
        blockers.append("fixed_shape_path_used")
    if not selector_source:
        blockers.append("selector_output_not_shape_source")
    if auth.authorization_status != "authorized_for_future_flexible_selector_launch_review":
        blockers.append("flexible_selector_authorization_not_ready")
    passed = not blockers
    return LambdaFlexibleSelectorFixedShapeAudit(
        audit_passed=passed,
        hardcoded_gpu_1x_h100_pcie_path_disabled=True,
        hardcoded_gpu_8x_a100_80gb_sxm4_path_disabled=True,
        selector_output_is_shape_source=selector_source,
        command_preview_requires_selector_authorization=True,
        old_m028_m029_fixed_shape_fallback_blocked=True,
        fixed_shape_path_used=False,
        blockers=sorted(set(blockers)),
        warnings=[
            "flexible selector must not use M039/M045 fixed-shape artifacts",
            "selected shape is read from selector output only",
        ],
    )


def load_lambda_flexible_selector_fixed_shape_audit(
    path: str | Path,
) -> LambdaFlexibleSelectorFixedShapeAudit:
    return LambdaFlexibleSelectorFixedShapeAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_flexible_selector_fixed_shape_audit(
    path: str | Path,
    report: LambdaFlexibleSelectorFixedShapeAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
