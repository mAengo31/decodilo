"""Preflight summaries for remote backend readiness evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.cloud.remote_backend_review_preflight import (
    collect_remote_backend_review_preflight,
)
from decodilo.storage.remote_backend_conformance import load_remote_backend_conformance_report
from decodilo.storage.remote_backend_evidence import load_remote_backend_evidence_package
from decodilo.storage.remote_backend_provider_matrix import load_provider_comparison_matrix
from decodilo.storage.remote_backend_readiness import load_remote_backend_readiness_report


def collect_remote_backend_readiness_preflight(
    *,
    root: str | Path,
) -> dict[str, Any]:
    base = Path(root)
    warnings: list[str] = []
    errors: list[str] = []
    summary: dict[str, Any] = {
        "remote_backend_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    readiness_path = base / "remote_backend_readiness.json"
    conformance_path = base / "remote_conformance.json"
    evidence_path = base / "remote_backend_evidence_package.json"
    provider_matrix_path = base / "provider_matrix.json"
    if readiness_path.exists():
        try:
            readiness = load_remote_backend_readiness_report(readiness_path)
            summary["readiness_path"] = str(readiness_path)
            summary["readiness_status"] = readiness.readiness_status.value
            summary["readiness_blockers"] = readiness.blockers
        except Exception as exc:  # noqa: BLE001 - preflight should summarize failures
            errors.append(f"remote readiness report unreadable: {exc}")
    else:
        warnings.append("remote backend readiness report missing")
    if conformance_path.exists():
        try:
            conformance = load_remote_backend_conformance_report(conformance_path)
            summary["conformance_path"] = str(conformance_path)
            summary["conformance_status"] = conformance.conformance_status
            summary["conformance_passed"] = conformance.passed
            if conformance.passed:
                warnings.append("simulator conformance is not production backend readiness")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"remote conformance report unreadable: {exc}")
    else:
        warnings.append("remote backend conformance report missing")
    if evidence_path.exists():
        try:
            evidence = load_remote_backend_evidence_package(evidence_path)
            summary["evidence_package_path"] = str(evidence_path)
            summary["evidence_completeness_score"] = (
                evidence.manifest.evidence_completeness_score
            )
            summary["evidence_blockers"] = evidence.manifest.blockers
        except Exception as exc:  # noqa: BLE001
            errors.append(f"remote evidence package unreadable: {exc}")
    else:
        warnings.append("remote backend evidence package missing")
    if provider_matrix_path.exists():
        try:
            matrix = load_provider_comparison_matrix(provider_matrix_path)
            summary["provider_matrix_path"] = str(provider_matrix_path)
            summary["provider_count"] = len(matrix.providers)
            summary["top_provider"] = (
                matrix.scores[0].provider_name if matrix.scores else None
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"provider matrix unreadable: {exc}")
    review = collect_remote_backend_review_preflight(root=base)
    summary["review_evidence"] = review["summary"]
    warnings.extend(review["warnings"])
    errors.extend(review["errors"])
    return {"summary": summary, "warnings": warnings, "errors": errors}
