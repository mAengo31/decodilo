from __future__ import annotations

from pathlib import Path

from lambda_m036_helpers import (
    ambiguous,
    endpoint_behavior,
    endpoint_upgrade,
    idempotency,
    lower_cost_review,
    response_shape,
    support_response,
    validation,
)

from decodilo.lambda_cloud.ambiguous_response_semantics import (
    write_lambda_ambiguous_response_semantics,
)
from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    write_lambda_endpoint_behavior_evidence,
)
from decodilo.lambda_cloud.endpoint_confidence_decision import (
    build_lambda_endpoint_confidence_decision,
)
from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    write_lambda_endpoint_confidence_upgrade_report,
)
from decodilo.lambda_cloud.idempotency_semantics_evidence import (
    write_lambda_idempotency_semantics_evidence,
)
from decodilo.lambda_cloud.lower_cost_reauthorization_package import (
    build_lambda_lower_cost_reauthorization_package,
)
from decodilo.lambda_cloud.lower_cost_shape_operator_selection import (
    build_lambda_lower_cost_shape_operator_selection,
)
from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    write_lambda_lower_cost_shape_reauthorization,
)
from decodilo.lambda_cloud.m037_decision_record import (
    build_lambda_m037_decision_record,
)
from decodilo.lambda_cloud.response_shape_evidence import (
    write_lambda_response_shape_evidence,
)
from decodilo.lambda_cloud.support_confirmation_request import (
    build_lambda_support_confirmation_request,
    write_lambda_support_confirmation_request_report,
)
from decodilo.lambda_cloud.support_confirmation_response import (
    write_lambda_support_confirmation_response,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    write_lambda_support_confirmation_validation_report,
)
from decodilo.lambda_cloud.support_response_evidence_package import (
    build_lambda_support_response_evidence_package,
)


def complete_support_paths(tmp_path: Path) -> dict[str, Path]:
    request = build_lambda_support_confirmation_request()
    response = support_response()
    valid = validation(response)
    behavior = endpoint_behavior(response=response, validation_report=valid)
    shape = response_shape()
    idem = idempotency()
    amb = ambiguous()
    upgrade = endpoint_upgrade()
    paths = {
        "support_request": tmp_path / "support-request.json",
        "support_response": tmp_path / "support-response.json",
        "validation": tmp_path / "validation.json",
        "endpoint_behavior": tmp_path / "endpoint-behavior.json",
        "response_shape": tmp_path / "response-shape.json",
        "idempotency": tmp_path / "idempotency.json",
        "ambiguous": tmp_path / "ambiguous.json",
        "upgrade": tmp_path / "upgrade.json",
    }
    write_lambda_support_confirmation_request_report(paths["support_request"], request)
    write_lambda_support_confirmation_response(paths["support_response"], response)
    write_lambda_support_confirmation_validation_report(paths["validation"], valid)
    write_lambda_endpoint_behavior_evidence(paths["endpoint_behavior"], behavior)
    write_lambda_response_shape_evidence(paths["response_shape"], shape)
    write_lambda_idempotency_semantics_evidence(paths["idempotency"], idem)
    write_lambda_ambiguous_response_semantics(paths["ambiguous"], amb)
    write_lambda_endpoint_confidence_upgrade_report(paths["upgrade"], upgrade)
    return paths


def support_package(tmp_path: Path):
    paths = complete_support_paths(tmp_path)
    return build_lambda_support_response_evidence_package(
        support_request=paths["support_request"],
        support_response=paths["support_response"],
        validation=paths["validation"],
        endpoint_behavior=paths["endpoint_behavior"],
        response_shape=paths["response_shape"],
        idempotency_semantics=paths["idempotency"],
        ambiguous_response_semantics=paths["ambiguous"],
        endpoint_confidence_upgrade=paths["upgrade"],
    )


def endpoint_decision():
    return build_lambda_endpoint_confidence_decision(
        validation=validation(),
        endpoint_confidence_upgrade=endpoint_upgrade(),
        endpoint_behavior=endpoint_behavior(),
    )


def shape_selection(*, pcie_available: bool = True):
    response = support_response(pcie_available=pcie_available)
    return build_lambda_lower_cost_shape_operator_selection(
        lower_cost_review=lower_cost_review(pcie_available=pcie_available),
        support_response=response,
    )


def reauth_package():
    return build_lambda_lower_cost_reauthorization_package(
        selection=shape_selection(),
        lower_cost_review=lower_cost_review(),
    )


def m037_decision(tmp_path: Path):
    return build_lambda_m037_decision_record(
        support_evidence_package=support_package(tmp_path),
        endpoint_decision=endpoint_decision(),
        shape_selection=shape_selection(),
        reauthorization_package=reauth_package(),
    )


def write_lower_cost_review(path: Path):
    report = lower_cost_review()
    write_lambda_lower_cost_shape_reauthorization(path, report)
    return path
