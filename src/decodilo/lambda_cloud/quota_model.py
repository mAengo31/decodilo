"""Planning-only quota model for fake Lambda discovery data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_models import LambdaQuota


class LambdaQuotaPlanningReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    quota: LambdaQuota
    requested_instances: int = Field(ge=0)
    requested_gpus: int = Field(ge=0)
    quota_allows_request: bool
    live_api_used: bool = False
    warnings: list[str] = Field(default_factory=list)


def evaluate_lambda_quota(
    quota: LambdaQuota,
    *,
    requested_instances: int,
    requested_gpus: int,
) -> LambdaQuotaPlanningReport:
    instance_ok = quota.max_instances is None or (
        quota.running_instances + requested_instances <= quota.max_instances
    )
    gpu_ok = quota.max_gpus is None or quota.running_gpus + requested_gpus <= quota.max_gpus
    return LambdaQuotaPlanningReport(
        quota=quota,
        requested_instances=requested_instances,
        requested_gpus=requested_gpus,
        quota_allows_request=instance_ok and gpu_ok,
        warnings=["quota is fixture-only and not live Lambda capacity"],
    )
