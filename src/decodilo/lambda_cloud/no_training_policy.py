"""No-training policy for Lambda remote bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

TRAINING_COMMAND_PATTERNS = (
    "train",
    "trainer",
    "torchrun",
    "accelerate launch",
    "datasets",
    "huggingface",
    "benchmark",
    "token",
    "model download",
)


class LambdaNoTrainingPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    no_training_policy_status: str = "training_denied"
    training_allowed: bool = False
    dataset_download_allowed: bool = False
    model_download_allowed: bool = False
    gpu_benchmark_allowed: bool = False
    long_running_process_allowed: bool = False
    blocked_command_patterns: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_training(self) -> LambdaNoTrainingPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.training_allowed
            or self.dataset_download_allowed
            or self.model_download_allowed
            or self.gpu_benchmark_allowed
            or self.long_running_process_allowed
        ):
            raise ValueError("no-training policy cannot allow training work")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaNoTrainingPolicy = LambdaNoTrainingPolicyReport


def build_lambda_no_training_policy() -> LambdaNoTrainingPolicyReport:
    return LambdaNoTrainingPolicyReport(
        blocked_command_patterns=list(TRAINING_COMMAND_PATTERNS),
        warnings=[
            "training, downloads, and benchmarks are denied for M051 bootstrap",
            "M053 carries no-training denial forward into SSH connectivity planning",
            "M058 carries no-training denial forward into identity-command review",
            "M062 carries no-training denial forward into GPU visibility review",
            "M064 carries no-training denial forward into Python version query review",
        ],
    )


def training_command_blocked(command: str) -> bool:
    lowered = command.lower()
    return any(pattern in lowered for pattern in TRAINING_COMMAND_PATTERNS)


def load_lambda_no_training_policy(path: str | Path) -> LambdaNoTrainingPolicyReport:
    return LambdaNoTrainingPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_no_training_policy(
    path: str | Path,
    report: LambdaNoTrainingPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
