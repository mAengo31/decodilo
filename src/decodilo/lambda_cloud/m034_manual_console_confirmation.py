"""Manual Lambda console confirmation records for M034C incidents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from decodilo.lambda_cloud.real_launch_result import redact_instance_id

LambdaM034ConsoleConfirmationStatus = Literal[
    "not_provided",
    "confirmed_no_visible_instances",
    "confirmed_manual_termination_performed",
    "unresolved",
]


class LambdaM034ManualConsoleConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True)

    confirmation_id: str = "lambda-m034-manual-console-confirmation"
    operator_name: str | None = None
    confirmation_time_utc: str | None = None
    lambda_console_checked: bool = False
    no_instances_visible: bool = False
    no_pending_instances_visible: bool = False
    no_alert_instances_visible: bool = False
    no_owned_instance_found: bool = False
    any_instance_terminated_manually: bool = False
    manually_terminated_instance_id_redacted: str | None = None
    notes: str | None = None
    confirmation_status: LambdaM034ConsoleConfirmationStatus = "not_provided"
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled_and_manual_termination(self) -> LambdaM034ManualConsoleConfirmation:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 manual console confirmation cannot enable launch")
        if (
            self.any_instance_terminated_manually
            and not self.manually_terminated_instance_id_redacted
        ):
            raise ValueError("manual termination requires redacted instance id")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM034ManualConsoleConfirmationReport(LambdaM034ManualConsoleConfirmation):
    pass


def build_lambda_m034_manual_console_confirmation(
    *,
    lambda_console_checked: bool = False,
    no_instances_visible: bool = False,
    no_pending_instances_visible: bool = False,
    no_alert_instances_visible: bool = False,
    no_owned_instance_found: bool | None = None,
    any_instance_terminated_manually: bool = False,
    manually_terminated_instance_id: str | None = None,
    operator_name: str | None = None,
    confirmation_time_utc: str | None = None,
    notes: str | None = None,
) -> LambdaM034ManualConsoleConfirmationReport:
    redacted = redact_instance_id(manually_terminated_instance_id)
    owned_not_found = (
        no_owned_instance_found
        if no_owned_instance_found is not None
        else bool(no_instances_visible and no_pending_instances_visible)
    )
    if not lambda_console_checked:
        status: LambdaM034ConsoleConfirmationStatus = "not_provided"
    elif any_instance_terminated_manually:
        status = "confirmed_manual_termination_performed" if redacted else "unresolved"
    elif no_instances_visible and no_pending_instances_visible and no_alert_instances_visible:
        status = "confirmed_no_visible_instances"
    else:
        status = "unresolved"
    return LambdaM034ManualConsoleConfirmationReport(
        operator_name=operator_name,
        confirmation_time_utc=confirmation_time_utc,
        lambda_console_checked=lambda_console_checked,
        no_instances_visible=no_instances_visible,
        no_pending_instances_visible=no_pending_instances_visible,
        no_alert_instances_visible=no_alert_instances_visible,
        no_owned_instance_found=owned_not_found,
        any_instance_terminated_manually=any_instance_terminated_manually,
        manually_terminated_instance_id_redacted=redacted,
        notes=notes,
        confirmation_status=status,
    )


def load_lambda_m034_manual_console_confirmation(
    path: str | Path,
) -> LambdaM034ManualConsoleConfirmationReport:
    return LambdaM034ManualConsoleConfirmationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_manual_console_confirmation(
    path: str | Path,
    report: LambdaM034ManualConsoleConfirmationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
