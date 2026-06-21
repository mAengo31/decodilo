"""Offline Lambda discovery from fixtures or fake transport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_models import (
    LambdaFilesystem,
    LambdaImage,
    LambdaInstance,
    LambdaInstanceType,
    LambdaQuota,
    LambdaRegion,
    LambdaSSHKey,
    LambdaUsageEstimate,
)
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient


class LambdaDiscoveryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    source: Literal["fixture", "fake_transport"]
    regions: list[LambdaRegion]
    instance_types: list[LambdaInstanceType]
    images: list[LambdaImage]
    ssh_keys: list[LambdaSSHKey]
    filesystems: list[LambdaFilesystem]
    running_instances: list[LambdaInstance]
    quota: LambdaQuota | None = None
    usage_estimate: LambdaUsageEstimate | None = None
    live_api_used: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_from_client(
    client: ReadOnlyLambdaCloudClient,
    *,
    source: Literal["fixture", "fake_transport"] = "fake_transport",
) -> LambdaDiscoveryReport:
    instances = client.list_instances()
    return LambdaDiscoveryReport(
        source=source,
        regions=client.list_regions(),
        instance_types=client.list_instance_types(),
        images=client.list_images(),
        ssh_keys=client.list_ssh_keys(),
        filesystems=client.list_filesystems(),
        running_instances=[
            instance for instance in instances if instance.status not in {"terminated", "stopped"}
        ],
        quota=client.get_quota(),
        usage_estimate=client.get_usage_estimate(),
    )


def load_lambda_discovery_report(path: str | Path) -> LambdaDiscoveryReport:
    return LambdaDiscoveryReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_discovery_report(path: str | Path, report: LambdaDiscoveryReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
