"""Remote-backend evidence checks for cloud preflight."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.cloud.remote_backend_readiness_preflight import (
    collect_remote_backend_readiness_preflight,
)
from decodilo.runtime.remote_backend_design_report import load_remote_backend_design_report
from decodilo.storage.remote_backend_requirements import load_remote_backend_requirements


def collect_remote_backend_preflight_evidence(
    *,
    root: str | Path,
) -> dict[str, Any]:
    base = Path(root)
    warnings: list[str] = [
        "remote artifact backend not implemented",
        "simulator pass is not production proof",
        "no credentials or real API integration",
        "no cloud launch enabled",
    ]
    errors: list[str] = []
    summary: dict[str, Any] = {
        "remote_backend_enabled": False,
        "requirements_path": None,
        "design_validation_path": None,
        "blockers": [],
    }
    req_path = base / "remote_backend_requirements.json"
    design_path = base / "remote_backend_design_validation.json"
    if req_path.exists():
        requirements = load_remote_backend_requirements(req_path)
        summary["requirements_path"] = str(req_path)
        summary["target_learner_count"] = requirements.target_learner_count
        summary["stress_learner_count"] = requirements.stress_learner_count
    else:
        warnings.append("remote backend requirements missing")
    if design_path.exists():
        report = load_remote_backend_design_report(design_path)
        summary["design_validation_path"] = str(design_path)
        summary["blockers"] = report.blockers
        if report.blockers:
            warnings.append("remote backend design blockers present")
    else:
        warnings.append("remote backend design validation report missing")
    readiness = collect_remote_backend_readiness_preflight(root=base)
    summary["readiness_evidence"] = readiness["summary"]
    warnings.extend(readiness["warnings"])
    errors.extend(readiness["errors"])
    return {"summary": summary, "warnings": warnings, "errors": errors}
