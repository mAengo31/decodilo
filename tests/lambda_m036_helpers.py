from __future__ import annotations

from pathlib import Path

from lambda_m035_helpers import price_snapshot

from decodilo.lambda_cloud.ambiguous_response_semantics import (
    build_lambda_ambiguous_response_semantics,
)
from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    build_lambda_endpoint_behavior_evidence,
)
from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    build_lambda_endpoint_confidence_upgrade,
)
from decodilo.lambda_cloud.idempotency_semantics_evidence import (
    build_lambda_idempotency_semantics_evidence,
)
from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    build_lambda_lower_cost_shape_reauthorization,
)
from decodilo.lambda_cloud.m036_strategy_decision import (
    build_lambda_m036_strategy_decision,
)
from decodilo.lambda_cloud.response_shape_evidence import (
    build_lambda_response_shape_evidence,
)
from decodilo.lambda_cloud.support_confirmation_response import (
    ingest_lambda_support_confirmation_response,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    validate_lambda_support_confirmation_response,
)
from decodilo.pricing.snapshots import write_price_snapshot


def support_payload(*, missing: tuple[str, ...] = (), pcie_available: bool = True):
    answers = {
        "launch_method": "POST",
        "launch_path_template": "/instance-operations/launch",
        "launch_required_fields": "instance_type, region",
        "launch_optional_fields": "name, client_token",
        "launch_omit_user_data": "Omit user_data, cloud_init, and setup_script fields.",
        "launch_idempotency": {
            "answer_text": "Client token is supported.",
            "structured_value": {
                "idempotency_supported": True,
                "field_name": "client_token",
                "client_token_supported": True,
                "duplicate_launch_behavior": "same client token is reconciled",
                "duplicate_terminate_behavior": "owned terminate is idempotent",
            },
        },
        "launch_success_status": {
            "answer_text": "200 or 202",
            "structured_value": {"values": [200, 202]},
        },
        "launch_content_type": "application/json",
        "launch_response_shape": "JSON object with data.instance_id on synchronous success.",
        "launch_instance_id_field": "data.instance_id",
        "launch_async_without_id": {"answer_text": "No", "structured_value": {"value": False}},
        "launch_timeout_may_create": {"answer_text": "Yes", "structured_value": {"value": True}},
        "ambiguous_launch_reconciliation": (
            "Use read-only list/get by shape, region, and request time; require manual review "
            "if no exact or high-confidence owned candidate exists."
        ),
        "terminate_method": "POST",
        "terminate_path_template": "/instance-operations/terminate",
        "terminate_required_fields": "instance_id",
        "terminate_success_status": {
            "answer_text": "200, 202, or 204",
            "structured_value": {"values": [200, 202, 204]},
        },
        "terminate_response_shape": "JSON or empty success body.",
        "termination_terminal_states": {
            "answer_text": "terminated",
            "structured_value": {"values": ["terminated", "absent"]},
        },
        "terminate_timeout_may_terminate": {
            "answer_text": "Yes",
            "structured_value": {"value": True},
        },
        "termination_verification": "Verify with read-only list/get until absent or terminated.",
        "list_instances_endpoint": "/instances",
        "list_pagination": "paginated",
        "list_region_scope": "region-scoped when region is supplied",
        "list_consistency": "eventually consistent for a short interval",
        "instance_type_listing": "may be account-specific or unsupported",
        "quota_endpoint": "unsupported for this account",
        "usage_endpoint": "unsupported for this account",
        "launch_rate_limits": "low rate; do not retry automatically",
        "terminate_rate_limits": "low rate; retry only owned terminate after verification",
        "read_rate_limits": "ordinary read/list limits",
        "safe_lifecycle_shape": {
            "answer_text": "Use gpu_1x_h100_pcie for lifecycle smoke if available.",
            "structured_value": {"shape": "gpu_1x_h100_pcie", "available": pcie_available},
        },
        "h100_pcie_1x_supported": {
            "answer_text": "Supported in the target account/region.",
            "structured_value": {"shape": "gpu_1x_h100_pcie", "available": pcie_available},
        },
        "lower_cost_non_h100_shape": {
            "answer_text": "Unknown.",
            "structured_value": {"shape": "gpu_1x_h100_pcie", "available": pcie_available},
        },
    }
    for key in missing:
        answers.pop(key, None)
    return {
        "source_type": "operator_confirmed_docs",
        "source_reference": "operator-support-fixture",
        "captured_at_utc": "2026-06-19T12:00:00Z",
        "confidence": "high",
        "answers": answers,
        "notes": "offline fixture, no secrets",
    }


def support_response(*, missing: tuple[str, ...] = (), pcie_available: bool = True):
    return ingest_lambda_support_confirmation_response(
        support_payload(missing=missing, pcie_available=pcie_available)
    )


def validation(response=None):
    return validate_lambda_support_confirmation_response(response or support_response())


def endpoint_behavior(response=None, validation_report=None):
    response = response or support_response()
    return build_lambda_endpoint_behavior_evidence(
        response=response,
        validation=validation_report or validation(response),
    )


def response_shape():
    return build_lambda_response_shape_evidence(endpoint_behavior())


def idempotency():
    return build_lambda_idempotency_semantics_evidence(support_response())


def ambiguous():
    return build_lambda_ambiguous_response_semantics(support_response())


def endpoint_upgrade():
    return build_lambda_endpoint_confidence_upgrade(
        support_validation=validation(),
        endpoint_behavior=endpoint_behavior(),
        response_shape=response_shape(),
        idempotency_semantics=idempotency(),
        ambiguous_response_semantics=ambiguous(),
    )


def lower_cost_review(*, pcie_available: bool = True):
    return build_lambda_lower_cost_shape_reauthorization(
        price_snapshot=price_snapshot(),
        current_shape="gpu_8x_h100_sxm",
        support_response=support_response(pcie_available=pcie_available),
    )


def strategy_decision():
    return build_lambda_m036_strategy_decision(
        endpoint_upgrade=endpoint_upgrade(),
        lower_cost_shape=lower_cost_review(),
    )


def write_support_response(path: Path, *, missing: tuple[str, ...] = ()) -> Path:
    response = support_response(missing=missing)
    path.write_text(response.to_json(), encoding="utf-8")
    return path


def write_price(path: Path) -> Path:
    write_price_snapshot(path, price_snapshot())
    return path
