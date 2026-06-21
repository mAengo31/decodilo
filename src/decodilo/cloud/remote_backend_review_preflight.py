"""Cloud/local preflight summaries for remote backend review packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.runtime.remote_backend_review_package import load_remote_backend_review_package
from decodilo.storage.remote_backend_decision_record import load_remote_backend_decision_record
from decodilo.storage.remote_backend_proposal import load_remote_backend_implementation_proposal
from decodilo.storage.remote_backend_risk_register import load_remote_backend_risk_register
from decodilo.storage.remote_backend_sdk_guard import load_remote_backend_sdk_guard_report


def collect_remote_backend_review_preflight(*, root: str | Path) -> dict[str, Any]:
    base = Path(root)
    warnings: list[str] = []
    errors: list[str] = []
    summary: dict[str, Any] = {
        "remote_backend_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    proposal_path = base / "remote-proposal.json"
    decision_path = base / "decision-record.json"
    sdk_guard_path = base / "sdk-guard.json"
    risk_path = base / "risk-register.json"
    review_path = base / "review-package.json"
    if proposal_path.exists():
        try:
            proposal = load_remote_backend_implementation_proposal(proposal_path)
            summary["proposal_path"] = str(proposal_path)
            summary["provider_candidate_name"] = proposal.provider_candidate_name
            summary["proposal_blockers"] = proposal.blockers
        except Exception as exc:  # noqa: BLE001
            errors.append(f"remote proposal unreadable: {exc}")
    else:
        warnings.append("remote backend implementation proposal missing")
    if decision_path.exists():
        try:
            decision = load_remote_backend_decision_record(decision_path)
            summary["decision_record_path"] = str(decision_path)
            summary["decision_status"] = decision.status.value
            summary["decision_blockers"] = decision.blockers
            if decision.status.value == "candidate_for_future_sdk_review":
                warnings.append("future SDK review candidate only; backend remains disabled")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"remote decision record unreadable: {exc}")
    else:
        warnings.append("remote backend decision record missing")
    if sdk_guard_path.exists():
        try:
            guard = load_remote_backend_sdk_guard_report(sdk_guard_path)
            summary["sdk_guard_path"] = str(sdk_guard_path)
            summary["sdk_guard_passed"] = guard.passed
            summary["sdk_guard_errors"] = guard.errors
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sdk guard report unreadable: {exc}")
    else:
        warnings.append("remote backend SDK guard report missing")
    if risk_path.exists():
        try:
            risk = load_remote_backend_risk_register(risk_path)
            summary["risk_register_path"] = str(risk_path)
            summary["risk_blockers"] = risk.blockers
        except Exception as exc:  # noqa: BLE001
            errors.append(f"risk register unreadable: {exc}")
    if review_path.exists():
        try:
            package = load_remote_backend_review_package(review_path)
            summary["review_package_path"] = str(review_path)
            summary["review_package_blockers"] = package.blockers
        except Exception as exc:  # noqa: BLE001
            errors.append(f"review package unreadable: {exc}")
    else:
        warnings.append("remote backend review package missing")
    return {"summary": summary, "warnings": warnings, "errors": errors}
