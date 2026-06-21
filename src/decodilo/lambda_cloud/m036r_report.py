"""M036R Strand CLI compatibility report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.strand_cli_compatibility import (
    StrandLambdaCLICompatibilityReport,
    load_strand_cli_compatibility_report,
)
from decodilo.lambda_cloud.strand_cli_gap_analysis import (
    StrandCLIGapAnalysisReport,
    load_strand_cli_gap_analysis,
)
from decodilo.lambda_cloud.strand_cli_migration_plan import StrandCLIMigrationPlan


class LambdaM036RReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    strand_cli_unofficial: bool = True
    compatibility_status: str
    gaps_found: int
    migration_required: bool
    fixes_applied_or_not_required: bool
    request_shape_matches_strand: bool
    launch_response_parser_accepts_data_instance_ids: bool
    terminate_empty_2xx_supported: bool
    ssh_key_required_for_real_launch: bool
    future_launch_review_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM036RReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M036R report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m036r_report(
    *,
    compatibility: StrandLambdaCLICompatibilityReport,
    gap_analysis: StrandCLIGapAnalysisReport,
    migration_plan: StrandCLIMigrationPlan,
) -> LambdaM036RReport:
    blockers = list(gap_analysis.launch_blockers)
    future_status = (
        "can_move_to_future_review"
        if not blockers and migration_plan.future_attempt_can_be_reviewed_after_migration
        else "blocked_until_migration"
    )
    return LambdaM036RReport(
        compatibility_status=compatibility.compatibility_status,
        gaps_found=len(gap_analysis.gaps),
        migration_required=gap_analysis.migration_required,
        fixes_applied_or_not_required=not blockers,
        request_shape_matches_strand=not any(
            gap.area in {"launch_payload_shape", "terminate_payload_shape"}
            for gap in gap_analysis.gaps
        ),
        launch_response_parser_accepts_data_instance_ids=not any(
            gap.area == "launch_response_parser" for gap in gap_analysis.gaps
        ),
        terminate_empty_2xx_supported=not any(
            gap.area == "terminate_empty_2xx" for gap in gap_analysis.gaps
        ),
        ssh_key_required_for_real_launch=not any(
            gap.area == "launch_payload_shape" for gap in gap_analysis.gaps
        ),
        future_launch_review_status=future_status,
        blockers=blockers,
        warnings=[
            *compatibility.warnings,
            *gap_analysis.warnings,
            *migration_plan.warnings,
            "M036R is no-launch/no-mutation compatibility evidence only",
        ],
    )


def build_lambda_m036r_report_from_paths(
    *,
    compatibility: str | Path,
    gap_analysis: str | Path,
    migration_plan: StrandCLIMigrationPlan,
) -> LambdaM036RReport:
    return build_lambda_m036r_report(
        compatibility=load_strand_cli_compatibility_report(compatibility),
        gap_analysis=load_strand_cli_gap_analysis(gap_analysis),
        migration_plan=migration_plan,
    )


def write_lambda_m036r_report(path: str | Path, report: LambdaM036RReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_m036r_report(path: str | Path) -> LambdaM036RReport:
    return LambdaM036RReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
