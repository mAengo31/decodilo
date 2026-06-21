"""M037 support/operator response evidence package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_response_secret_scan import (
    LambdaSupportResponseSecretScanReport,
    scan_lambda_support_response_path,
)


class LambdaSupportResponseEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    ref: str | None = None
    sha256: str | None = None
    present: bool = False


class LambdaSupportResponseEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    package_id: str = "lambda-m037-support-response-evidence-package"
    support_request: LambdaSupportResponseEvidenceItem
    support_response: LambdaSupportResponseEvidenceItem
    validation_report: LambdaSupportResponseEvidenceItem
    endpoint_behavior_evidence: LambdaSupportResponseEvidenceItem
    response_shape_evidence: LambdaSupportResponseEvidenceItem
    idempotency_semantics: LambdaSupportResponseEvidenceItem
    ambiguous_response_semantics: LambdaSupportResponseEvidenceItem
    endpoint_confidence_upgrade: LambdaSupportResponseEvidenceItem
    secret_scan: LambdaSupportResponseSecretScanReport
    package_passed: bool
    missing_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportResponseEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("support response evidence package cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_support_response_evidence_package(
    *,
    support_request: str | Path | None = None,
    support_response: str | Path | None = None,
    validation: str | Path | None = None,
    endpoint_behavior: str | Path | None = None,
    response_shape: str | Path | None = None,
    idempotency_semantics: str | Path | None = None,
    ambiguous_response_semantics: str | Path | None = None,
    endpoint_confidence_upgrade: str | Path | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> LambdaSupportResponseEvidencePackage:
    expected_hashes = expected_hashes or {}
    items = {
        "support_request": _item("support_request", support_request),
        "support_response": _item("support_response", support_response),
        "validation_report": _item("validation_report", validation),
        "endpoint_behavior_evidence": _item(
            "endpoint_behavior_evidence", endpoint_behavior
        ),
        "response_shape_evidence": _item("response_shape_evidence", response_shape),
        "idempotency_semantics": _item(
            "idempotency_semantics", idempotency_semantics
        ),
        "ambiguous_response_semantics": _item(
            "ambiguous_response_semantics", ambiguous_response_semantics
        ),
        "endpoint_confidence_upgrade": _item(
            "endpoint_confidence_upgrade", endpoint_confidence_upgrade
        ),
    }
    missing = [name for name, item in items.items() if not item.present]
    blockers = [f"{name}_missing" for name in missing]
    for name, expected in expected_hashes.items():
        actual = items.get(name)
        if actual is None or actual.sha256 != expected:
            blockers.append(f"{name}_hash_mismatch")
    secret_scan = (
        scan_lambda_support_response_path(support_response)
        if support_response is not None
        else LambdaSupportResponseSecretScanReport(
            scanned_ref=None,
            scan_passed=False,
            blockers=["support_response_missing"],
        )
    )
    blockers.extend(secret_scan.blockers)
    return LambdaSupportResponseEvidencePackage(
        support_request=items["support_request"],
        support_response=items["support_response"],
        validation_report=items["validation_report"],
        endpoint_behavior_evidence=items["endpoint_behavior_evidence"],
        response_shape_evidence=items["response_shape_evidence"],
        idempotency_semantics=items["idempotency_semantics"],
        ambiguous_response_semantics=items["ambiguous_response_semantics"],
        endpoint_confidence_upgrade=items["endpoint_confidence_upgrade"],
        secret_scan=secret_scan,
        package_passed=not blockers,
        missing_items=missing,
        blockers=sorted(set(blockers)),
        warnings=["support response evidence package is review-only"],
    )


def _item(name: str, value: str | Path | None) -> LambdaSupportResponseEvidenceItem:
    if value is None:
        return LambdaSupportResponseEvidenceItem(name=name)
    target = Path(value)
    if not target.exists():
        return LambdaSupportResponseEvidenceItem(name=name, ref=str(target))
    return LambdaSupportResponseEvidenceItem(
        name=name,
        ref=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        present=True,
    )


def load_lambda_support_response_evidence_package(
    path: str | Path,
) -> LambdaSupportResponseEvidencePackage:
    return LambdaSupportResponseEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_response_evidence_package(
    path: str | Path,
    package: LambdaSupportResponseEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
