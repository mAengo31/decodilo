"""M047 closeout report for successful Lambda lifecycle smoke."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    load_lambda_lifecycle_smoke_closeout,
)
from decodilo.lambda_cloud.lifecycle_smoke_evidence_package import (
    load_lambda_lifecycle_smoke_evidence_package,
)
from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    load_lambda_lifecycle_smoke_postrun_reconciliation,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)
from decodilo.lambda_cloud.live_instance_type_parser import (
    load_lambda_live_instance_type_parser,
)
from decodilo.lambda_cloud.live_region_selection import load_lambda_live_region_selection
from decodilo.lambda_cloud.live_shape_alias_resolution import (
    load_lambda_live_shape_alias_resolution,
)
from decodilo.lambda_cloud.live_shape_price_join import load_lambda_live_shape_price_join
from decodilo.lambda_cloud.successful_launch_strategy_update import (
    load_lambda_successful_launch_strategy_update,
)


class LambdaM047Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    success_record_status: str
    reconciliation_status: str
    evidence_package_status: str
    closeout_status: str
    live_parser_status: str | None = None
    live_region_selection: str | None = None
    alias_resolution_status: str | None = None
    price_join_status: str | None = None
    strategy_update_status: str | None = None
    selected_candidate: str | None = None
    selected_region: str | None = None
    report_passed: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_m047_disabled(self) -> LambdaM047Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M047 report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m047_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    live_region_selection: str | Path,
    evidence_package: str | Path | None = None,
    live_parser: str | Path | None = None,
    alias_resolution: str | Path | None = None,
    price_join: str | Path | None = None,
    strategy_update: str | Path | None = None,
) -> LambdaM047Report:
    success = load_lambda_lifecycle_smoke_success_record(success_record)
    reconcile = load_lambda_lifecycle_smoke_postrun_reconciliation(reconciliation)
    close = load_lambda_lifecycle_smoke_closeout(closeout)
    region = load_lambda_live_region_selection(live_region_selection)
    evidence = (
        None
        if evidence_package is None or not Path(evidence_package).exists()
        else load_lambda_lifecycle_smoke_evidence_package(evidence_package)
    )
    parser = (
        None
        if live_parser is None or not Path(live_parser).exists()
        else load_lambda_live_instance_type_parser(live_parser)
    )
    alias = (
        None
        if alias_resolution is None or not Path(alias_resolution).exists()
        else load_lambda_live_shape_alias_resolution(alias_resolution)
    )
    price = (
        None
        if price_join is None or not Path(price_join).exists()
        else load_lambda_live_shape_price_join(price_join)
    )
    strategy = (
        None
        if strategy_update is None or not Path(strategy_update).exists()
        else load_lambda_successful_launch_strategy_update(strategy_update)
    )
    blockers = [
        *success.blockers,
        *reconcile.errors,
        *close.blockers,
        *region.blockers,
        *(evidence.blockers if evidence is not None else []),
        *(parser.blockers if parser is not None else []),
        *(alias.blockers if alias is not None else []),
        *(price.blockers if price is not None else []),
        *(strategy.blockers if strategy is not None else []),
    ]
    if success.status != "lifecycle_smoke_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("closeout_not_succeeded")
    if not region.selection_passed:
        blockers.append("live_region_selection_not_passed")
    return LambdaM047Report(
        success_record_status=success.status,
        reconciliation_status=(
            "passed" if reconcile.reconciliation_passed else "blocked"
        ),
        evidence_package_status=(
            "not_provided"
            if evidence is None
            else ("complete" if evidence.evidence_complete else "blocked")
        ),
        closeout_status=close.closeout_status,
        live_parser_status=None if parser is None else parser.parser_status,
        live_region_selection=region.selected_region,
        alias_resolution_status=None if alias is None else alias.alias_status,
        price_join_status=None if price is None else price.join_status,
        strategy_update_status=(
            None
            if strategy is None
            else ("success" if strategy.lifecycle_smoke_successful else "blocked")
        ),
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        report_passed=not blockers,
        historical_billable_action_performed=success.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M047 is closeout-only and performs no Lambda mutation",
                    *success.warnings,
                    *reconcile.warnings,
                    *close.warnings,
                    *region.warnings,
                    *(evidence.warnings if evidence is not None else []),
                    *(parser.warnings if parser is not None else []),
                    *(alias.warnings if alias is not None else []),
                    *(price.warnings if price is not None else []),
                    *(strategy.warnings if strategy is not None else []),
                ]
            )
        ),
    )


def load_lambda_m047_report(path: str | Path) -> LambdaM047Report:
    return LambdaM047Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m047_report(path: str | Path, report: LambdaM047Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
