"""File-transfer prohibition for SSH-connectivity-only Lambda review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaFileTransferProhibitionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prohibition_status: str = "file_transfer_prohibited"
    scp_allowed: bool = False
    sftp_allowed: bool = False
    rsync_allowed: bool = False
    upload_allowed: bool = False
    download_allowed: bool = False
    file_transfer_flags_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_transfer(self) -> LambdaFileTransferProhibitionPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.scp_allowed
            or self.sftp_allowed
            or self.rsync_allowed
            or self.upload_allowed
            or self.download_allowed
            or self.file_transfer_flags_allowed
        ):
            raise ValueError("file transfer prohibition cannot allow transfer")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_file_transfer_prohibition_policy() -> LambdaFileTransferProhibitionPolicy:
    return LambdaFileTransferProhibitionPolicy(
        warnings=[
            "M053 SSH connectivity-only review prohibits scp, sftp, rsync, upload, and download"
        ],
    )


def load_lambda_file_transfer_prohibition_policy(
    path: str | Path,
) -> LambdaFileTransferProhibitionPolicy:
    return LambdaFileTransferProhibitionPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_file_transfer_prohibition_policy(
    path: str | Path,
    report: LambdaFileTransferProhibitionPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
