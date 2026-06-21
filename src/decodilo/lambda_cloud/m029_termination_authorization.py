"""M028 termination authorization for future M029 owned-resource teardown."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaM029TerminationAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_id: str = "lambda-m029-termination-authorization"
    authorized_for: str = "M029_terminate_owned_instance_only"
    terminate_only_owned_instance: bool = True
    verify_termination_required: bool = True
    terminate_unowned_forbidden: bool = True
    authorized_operations: list[str] = Field(
        default_factory=lambda: [
            "terminate_owned_instance",
            "read_only_verify_terminated",
        ]
    )
    forbidden_operations: list[str] = Field(
        default_factory=lambda: [
            "terminate_unowned_instance",
            "restart",
            "create/delete SSH key",
            "create/delete filesystem",
        ]
    )
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM029TerminationAuthorization:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M029 termination authorization cannot enable launch in M028")
        if not self.terminate_only_owned_instance or not self.terminate_unowned_forbidden:
            raise ValueError("termination authorization must be owned-resource only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_termination_authorization() -> LambdaM029TerminationAuthorization:
    return LambdaM029TerminationAuthorization()


def load_lambda_m029_termination_authorization(
    path: str | Path,
) -> LambdaM029TerminationAuthorization:
    return LambdaM029TerminationAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m029_termination_authorization(
    path: str | Path,
    authorization: LambdaM029TerminationAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")

