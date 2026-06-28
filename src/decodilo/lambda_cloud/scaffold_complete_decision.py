"""M088 decision record that closes scaffold-validation phase."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaScaffoldCompleteStatus = Literal[
    "scaffold_validation_complete",
    "scaffold_validation_incomplete",
]


class LambdaScaffoldCompleteDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    scaffold_status: LambdaScaffoldCompleteStatus
    completed_layers: list[str] = Field(default_factory=list)
    next_phase: str = "bounded_synthetic_diloco_experiment"
    no_more_independent_smoke_categories_by_default: bool = True
    future_live_work_should_run_bounded_experiment_manifests: bool = True
    future_scaffold_exception_requires_concrete_failure: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_decision(self) -> LambdaScaffoldCompleteDecision:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("scaffold-complete decision must remain offline")
        if self.scaffold_status == "scaffold_validation_complete" and self.blockers:
            raise ValueError("complete scaffold decision cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_scaffold_complete_decision_from_paths(
    *,
    runtime_smoke_closeout: str | Path,
    learner_syncer_closeout: str | Path,
    diloco_synthetic_closeout: str | Path,
    optimizer_closeout: str | Path,
    integrated_closeout: str | Path,
    parameter_fragment_closeout: str | Path,
) -> LambdaScaffoldCompleteDecision:
    inputs = {
        "remote runtime/protocol smoke": Path(runtime_smoke_closeout),
        "remote learner/syncer synthetic smoke": Path(learner_syncer_closeout),
        "remote DiLoCo-shaped protocol smoke": Path(diloco_synthetic_closeout),
        "remote optimizer-fidelity smoke": Path(optimizer_closeout),
        "remote integrated protocol+optimizer smoke": Path(integrated_closeout),
        "remote parameter-fragment synthetic smoke": Path(parameter_fragment_closeout),
    }
    blockers: list[str] = []
    completed_layers: list[str] = []
    for layer, path in inputs.items():
        if not path.exists():
            blockers.append(f"{_slug(layer)}_closeout_missing")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("closeout_succeeded") is True:
            completed_layers.append(layer)
        else:
            blockers.append(f"{_slug(layer)}_closeout_not_succeeded")
        if data.get("launch_ready") or data.get("launch_allowed"):
            blockers.append(f"{_slug(layer)}_launch_flags_enabled")
    return LambdaScaffoldCompleteDecision(
        scaffold_status=(
            "scaffold_validation_complete"
            if not blockers
            else "scaffold_validation_incomplete"
        ),
        completed_layers=completed_layers,
        blockers=blockers,
        warnings=[
            "M088 ends the standalone scaffold-smoke progression by default",
            "future live work should move to complete bounded experiment manifests",
        ],
    )


def load_lambda_scaffold_complete_decision(
    path: str | Path,
) -> LambdaScaffoldCompleteDecision:
    return LambdaScaffoldCompleteDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_scaffold_complete_decision(
    path: str | Path,
    report: LambdaScaffoldCompleteDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _slug(value: str) -> str:
    return value.replace("/", "_").replace("+", "_").replace("-", "_").replace(" ", "_")
