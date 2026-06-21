"""Lambda live read-only discovery orchestration."""

from __future__ import annotations

from collections.abc import Callable

from decodilo.lambda_cloud.api_models import LambdaInstance
from decodilo.lambda_cloud.endpoint_calibration import (
    LambdaEndpointResult,
    build_lambda_endpoint_calibration_report,
    endpoint_result_for_failure,
    endpoint_result_for_success,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
)
from decodilo.lambda_cloud.live_endpoint_coverage import (
    build_lambda_endpoint_coverage_report,
)
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient

EndpointSet = str

_ENDPOINT_SETS: dict[EndpointSet, tuple[str, ...]] = {
    "minimal": ("list_instance_types", "list_instances"),
    "standard": (
        "list_instance_types",
        "list_regions",
        "list_images",
        "list_ssh_keys",
        "list_filesystems",
        "list_instances",
        "get_quota",
        "get_usage_estimate",
    ),
    "extended": (
        "list_instance_types",
        "list_regions",
        "list_images",
        "list_ssh_keys",
        "list_filesystems",
        "list_instances",
        "get_quota",
        "get_usage_estimate",
    ),
}


def run_lambda_live_discovery(
    client: LiveReadOnlyLambdaCloudClient,
    *,
    fail_on_partial: bool = False,
    source: str = "live_read_only",
    endpoint_set: EndpointSet = "standard",
    max_pages: int = 10,
    max_items: int = 1000,
    redaction_mode: str = "local_private_report",
) -> LambdaLiveDiscoveryReport:
    errors: list[str] = []
    warnings: list[str] = []
    if endpoint_set not in _ENDPOINT_SETS:
        raise ValueError(f"unsupported Lambda endpoint set: {endpoint_set}")
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if max_items <= 0:
        raise ValueError("max_items must be positive")
    endpoint_results: list[LambdaEndpointResult] = []
    values: dict[str, object] = {
        "list_regions": [],
        "list_instance_types": [],
        "list_images": [],
        "list_ssh_keys": [],
        "list_filesystems": [],
        "list_instances": [],
        "get_quota": None,
        "get_usage_estimate": None,
    }
    callables: dict[str, Callable[[], object]] = {
        "list_regions": client.list_regions,
        "list_instance_types": client.list_instance_types,
        "list_images": client.list_images,
        "list_ssh_keys": client.list_ssh_keys,
        "list_filesystems": client.list_filesystems,
        "list_instances": client.list_instances,
        "get_quota": client.get_quota,
        "get_usage_estimate": client.get_usage_estimate,
    }
    for operation in _ENDPOINT_SETS[endpoint_set]:
        value, result = _safe_call(
            operation,
            callables[operation],
            errors,
            warnings,
            fail_on_partial,
            client,
            max_items=max_items,
            source=source,
        )
        values[operation] = value
        endpoint_results.append(result)
    if errors:
        warnings.append("partial Lambda read-only discovery; one or more endpoints failed")
    regions = values["list_regions"]
    instance_types = values["list_instance_types"]
    images = values["list_images"]
    ssh_keys = values["list_ssh_keys"]
    filesystems = values["list_filesystems"]
    instances = values["list_instances"]
    quota = values["get_quota"]
    usage = values["get_usage_estimate"]
    unmanaged = [
        instance.instance_id
        for instance in instances
        if isinstance(instance, LambdaInstance) and not instance.tags.get("decodilo_run_id")
    ]
    calibration = build_lambda_endpoint_calibration_report(
        endpoint_results,
        warnings=warnings,
        errors=errors,
    )
    coverage = build_lambda_endpoint_coverage_report(
        endpoint_set=endpoint_set,
        expected_operations=list(_ENDPOINT_SETS[endpoint_set]),
        results=endpoint_results,
    )
    return LambdaLiveDiscoveryReport(
        source=source,  # type: ignore[arg-type]
        live_api_used=source == "live_read_only",
        regions=regions,  # type: ignore[arg-type]
        instance_types=instance_types,  # type: ignore[arg-type]
        images=images,  # type: ignore[arg-type]
        ssh_keys=ssh_keys,  # type: ignore[arg-type]
        filesystems=filesystems,  # type: ignore[arg-type]
        instances=instances,  # type: ignore[arg-type]
        quota=quota,  # type: ignore[arg-type]
        usage_estimate=usage,  # type: ignore[arg-type]
        unmanaged_instances=unmanaged,
        endpoint_set=endpoint_set,  # type: ignore[arg-type]
        endpoint_results=endpoint_results,
        endpoint_coverage=coverage,
        endpoint_count_attempted=calibration.endpoint_count_attempted,
        endpoint_count_succeeded=calibration.endpoint_count_succeeded,
        endpoint_count_failed=calibration.endpoint_count_failed,
        endpoint_count_failed_required=calibration.endpoint_count_failed_required,
        endpoint_count_failed_optional=calibration.endpoint_count_failed_optional,
        endpoint_count_unsupported_optional=calibration.endpoint_count_unsupported_optional,
        required_endpoint_success=calibration.required_endpoint_success,
        optional_endpoint_warnings=calibration.optional_endpoint_warnings,
        pagination_observed=any(result.pagination_observed for result in endpoint_results),
        redaction_mode=redaction_mode,  # type: ignore[arg-type]
        errors=errors,
        warnings=warnings,
        audit_log=list(client.audit_log),
    )


def _safe_call(
    name: str,
    fn: Callable[[], object],
    errors: list[str],
    warnings: list[str],
    fail_on_partial: bool,
    client: LiveReadOnlyLambdaCloudClient,
    *,
    max_items: int,
    source: str,
) -> tuple[object, LambdaEndpointResult]:
    start_audit = len(client.audit_log)
    try:
        value = fn()
        audit_entry = _latest_audit_entry(client, start_audit)
        if isinstance(value, list) and len(value) > max_items:
            warnings.append(f"{name}: max_items reached; result truncated")
            value = value[:max_items]
        return value, endpoint_result_for_success(
            operation=name,
            payload=value,
            audit_entry=audit_entry,
            live_api_used=source == "live_read_only",
        )
    except Exception as exc:
        message = f"{name}: {exc}"
        errors.append(message)
        audit_entry = _latest_audit_entry(client, start_audit)
        result = endpoint_result_for_failure(
            operation=name,
            exc=exc,
            audit_entry=audit_entry,
            live_api_used=source == "live_read_only",
        )
        if fail_on_partial:
            raise
        if name.startswith("list_"):
            return [], result
        return None, result


def _latest_audit_entry(
    client: LiveReadOnlyLambdaCloudClient,
    start_audit: int,
):
    entries = client.audit_log[start_audit:]
    if not entries:
        return None
    return entries[-1]
