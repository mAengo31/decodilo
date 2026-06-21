"""Runtime helpers for assembling remote backend evidence packages."""

from __future__ import annotations

from pathlib import Path

from decodilo.storage.remote_backend_evidence import (
    RemoteBackendEvidencePackage,
    build_remote_backend_evidence_package,
    write_remote_backend_evidence_package,
)


def build_remote_backend_evidence_package_from_paths(
    *,
    workdir: str | Path,
    scaling_report: str | Path | None,
    requirements: str | Path | None,
    validation_report: str | Path | None,
    conformance_report: str | Path | None,
    security_report: str | Path | None,
    cost_report: str | Path | None,
    readiness_report: str | Path | None,
) -> RemoteBackendEvidencePackage:
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    evidence_paths = {
        "learner_scaling_report": scaling_report,
        "remote_requirements": requirements,
        "design_validation_report": validation_report,
        "conformance_report": conformance_report,
        "security_report": security_report,
        "cost_estimate": cost_report,
        "readiness_report": readiness_report,
    }
    return build_remote_backend_evidence_package(
        evidence_paths=evidence_paths,
        scenario_id=root.name or "remote-backend-evidence",
    )


def write_runtime_remote_backend_evidence_package(
    path: str | Path,
    package: RemoteBackendEvidencePackage,
) -> None:
    write_remote_backend_evidence_package(path, package)
