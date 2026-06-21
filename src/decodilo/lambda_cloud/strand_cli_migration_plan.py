"""Migration plan for Strand CLI compatibility gaps."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.strand_cli_gap_analysis import (
    StrandCLIGapAnalysisReport,
    load_strand_cli_gap_analysis,
)


class StrandCLIMigrationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    migration_required: bool
    required_code_changes: list[str] = Field(default_factory=list)
    required_test_changes: list[str] = Field(default_factory=list)
    required_launch_gate_changes: list[str] = Field(default_factory=list)
    m034_attempt_should_remain_blocked: bool
    future_attempt_can_be_reviewed_after_migration: bool
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> StrandCLIMigrationPlan:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("Strand migration plan cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_strand_cli_migration_plan(
    gap_analysis: StrandCLIGapAnalysisReport,
) -> StrandCLIMigrationPlan:
    if not gap_analysis.migration_required:
        return StrandCLIMigrationPlan(
            migration_required=False,
            m034_attempt_should_remain_blocked=False,
            future_attempt_can_be_reviewed_after_migration=True,
            warnings=[
                "Strand compatibility gaps are closed for future review only; no launch authorized"
            ],
        )
    areas = {gap.area for gap in gap_analysis.gaps}
    code_changes: list[str] = []
    test_changes: list[str] = []
    gate_changes: list[str] = []
    if "timeout" in areas:
        code_changes.append("align mutation transport default timeout with Strand 30 seconds")
        test_changes.append("cover 30-second default timeout")
    if "launch_endpoint" in areas or "launch_method" in areas:
        code_changes.append("align launch endpoint with POST /instance-operations/launch")
    if "terminate_endpoint" in areas or "terminate_method" in areas:
        code_changes.append("align terminate endpoint with POST /instance-operations/terminate")
    if "launch_payload_shape" in areas:
        code_changes.append("emit region_name, instance_type_name, ssh_key_names, quantity")
        gate_changes.append("require existing SSH key name before future real launch")
    if "launch_response_parser" in areas:
        code_changes.append("parse launch data.instance_ids[0]")
    if "terminate_empty_2xx" in areas:
        code_changes.append("treat terminate 2xx empty body as success")
    return StrandCLIMigrationPlan(
        migration_required=True,
        required_code_changes=code_changes,
        required_test_changes=test_changes,
        required_launch_gate_changes=gate_changes,
        m034_attempt_should_remain_blocked=True,
        future_attempt_can_be_reviewed_after_migration=False,
        warnings=["Apply migration before any future launch review"],
    )


def build_strand_cli_migration_plan_from_path(
    gap_analysis: str | Path,
) -> StrandCLIMigrationPlan:
    return build_strand_cli_migration_plan(load_strand_cli_gap_analysis(gap_analysis))


def write_strand_cli_migration_plan(path: str | Path, plan: StrandCLIMigrationPlan) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
