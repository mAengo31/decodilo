"""Package-install policy for Lambda remote bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

PACKAGE_INSTALL_PATTERNS = (
    "apt install",
    "apt-get install",
    "pip install",
    "python -m pip install",
    "conda install",
    "mamba install",
    "git clone",
    "docker pull",
    "curl ",
    "wget ",
)


class LambdaPackageInstallPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    package_install_policy_status: str = "package_install_denied"
    package_install_allowed: bool = False
    blocked_command_patterns: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_denied(self) -> LambdaPackageInstallPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.package_install_allowed
        ):
            raise ValueError("package install policy must deny installs for M050")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaPackageInstallPolicy = LambdaPackageInstallPolicyReport


def build_lambda_package_install_policy() -> LambdaPackageInstallPolicyReport:
    return LambdaPackageInstallPolicyReport(
        blocked_command_patterns=list(PACKAGE_INSTALL_PATTERNS),
        warnings=[
            "package installation is denied for M051 bootstrap planning",
            "M053 carries package-install denial forward into SSH connectivity planning",
        ],
    )


def package_install_command_blocked(command: str) -> bool:
    lowered = command.lower()
    return any(pattern in lowered for pattern in PACKAGE_INSTALL_PATTERNS)


def load_lambda_package_install_policy(path: str | Path) -> LambdaPackageInstallPolicyReport:
    return LambdaPackageInstallPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_package_install_policy(
    path: str | Path,
    report: LambdaPackageInstallPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
