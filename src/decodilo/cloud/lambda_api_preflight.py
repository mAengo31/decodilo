"""Cloud/local preflight summary for offline Lambda API evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.lambda_cloud.discovery import load_lambda_discovery_report
from decodilo.lambda_cloud.evidence_freshness import load_lambda_evidence_freshness_report
from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.live_resource_ledger import load_lambda_live_ledger_report
from decodilo.lambda_cloud.m027_authorization_record import (
    load_lambda_m027_authorization_record,
)
from decodilo.lambda_cloud.m028_report import load_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.minimal_mutation_audit import (
    load_lambda_minimal_mutation_audit_report,
)
from decodilo.lambda_cloud.minimal_mutation_preflight import (
    load_lambda_minimal_mutation_preflight_report,
)
from decodilo.lambda_cloud.preflight import load_lambda_preflight_report
from decodilo.lambda_cloud.read_only_audit import load_lambda_read_only_audit_report
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    load_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_record import (
    load_lambda_real_launch_decision_record,
)
from decodilo.lambda_cloud.resource_ledger import load_lambda_ledger_report


def collect_lambda_api_preflight_evidence(*, root: str | Path) -> dict[str, Any]:
    base = Path(root)
    warnings = [
        "Lambda launch, termination, restart, create, and delete remain disabled",
    ]
    errors: list[str] = []
    summary: dict[str, Any] = {
        "lambda_api_live_used": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    discovery_path = base / "lambda-discovery.json"
    live_discovery_path = base / "lambda-live-discovery.json"
    read_only_audit_path = base / "lambda-read-only-audit.json"
    ledger_path = base / "lambda-ledger.json"
    live_ledger_path = base / "lambda-live-ledger.json"
    preflight_path = base / "lambda-preflight.json"
    live_preflight_path = base / "lambda-live-preflight.json"
    m026_decision_path = base / "lambda-m026-decision.json"
    m027_authorization_path = base / "lambda-m027-authorization.json"
    m026_blocker_matrix_path = base / "lambda-blocker-matrix.json"
    m026_freshness_path = base / "lambda-evidence-freshness.json"
    m027_minimal_preflight_path = base / "lambda-minimal-mutation-preflight.json"
    m027_minimal_audit_path = base / "lambda-minimal-mutation-audit.json"
    m028_report_path = base / "lambda-m028-report.json"
    m029_authorization_path = base / "lambda-m029-authorization.json"
    if discovery_path.exists():
        try:
            discovery = load_lambda_discovery_report(discovery_path)
            summary["discovery"] = {
                "path": str(discovery_path),
                "source": discovery.source,
                "live_api_used": discovery.live_api_used,
                "regions": len(discovery.regions),
                "instance_types": len(discovery.instance_types),
            }
            if discovery.live_api_used:
                errors.append("Lambda discovery unexpectedly used live API")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda discovery unreadable: {exc}")
    else:
        warnings.append("Lambda discovery report missing")
    if live_discovery_path.exists():
        try:
            live_discovery = load_lambda_live_discovery_report(live_discovery_path)
            summary["live_discovery"] = {
                "path": str(live_discovery_path),
                "source": live_discovery.source,
                "live_api_used": live_discovery.live_api_used,
                "read_only_mode": live_discovery.read_only_mode,
                "read_operations": len(live_discovery.audit_log),
                "billable_action_performed": live_discovery.billable_action_performed,
            }
            if live_discovery.billable_action_performed:
                errors.append("Lambda live discovery reported billable action")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda live discovery unreadable: {exc}")
    if read_only_audit_path.exists():
        try:
            audit = load_lambda_read_only_audit_report(read_only_audit_path)
            summary["read_only_audit"] = {
                "path": str(read_only_audit_path),
                "passed": audit.passed,
                "read_operations": audit.read_operations,
                "mutating_operations": audit.mutating_operations,
                "billable_action_performed": audit.billable_action_performed,
            }
            if not audit.passed:
                errors.extend(f"Lambda audit: {error}" for error in audit.errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda read-only audit unreadable: {exc}")
    if ledger_path.exists():
        try:
            ledger = load_lambda_ledger_report(ledger_path)
            summary["ledger"] = {
                "path": str(ledger_path),
                "planned_count": ledger.planned_count,
                "unmanaged_count": ledger.unmanaged_count,
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda resource ledger unreadable: {exc}")
    else:
        warnings.append("Lambda resource ledger missing")
    if live_ledger_path.exists():
        try:
            live_ledger = load_lambda_live_ledger_report(live_ledger_path)
            summary["live_ledger"] = {
                "path": str(live_ledger_path),
                "planned_count": live_ledger.planned_count,
                "unmanaged_count": live_ledger.unmanaged_count,
                "no_mutations_performed": live_ledger.no_mutations_performed,
            }
            if not live_ledger.no_mutations_performed:
                errors.append("Lambda live ledger reported mutation")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda live resource ledger unreadable: {exc}")
    if preflight_path.exists():
        try:
            preflight = load_lambda_preflight_report(preflight_path)
            summary["lambda_preflight"] = {
                "path": str(preflight_path),
                "passed": preflight.passed,
                "launch_ready": preflight.launch_ready,
                "launch_allowed": preflight.launch_allowed,
                "errors": preflight.errors,
            }
            warnings.extend(preflight.warnings)
            errors.extend(preflight.errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda preflight unreadable: {exc}")
    else:
        warnings.append("Lambda preflight report missing")
    if live_preflight_path.exists():
        try:
            live_preflight = load_lambda_preflight_report(live_preflight_path)
            summary["lambda_live_preflight"] = {
                "path": str(live_preflight_path),
                "passed": live_preflight.passed,
                "launch_ready": live_preflight.launch_ready,
                "launch_allowed": live_preflight.launch_allowed,
                "errors": live_preflight.errors,
            }
            warnings.extend(live_preflight.warnings)
            errors.extend(live_preflight.errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda live preflight unreadable: {exc}")
    if m026_decision_path.exists():
        try:
            decision = load_lambda_real_launch_decision_record(m026_decision_path)
            summary["m026_decision"] = {
                "path": str(m026_decision_path),
                "status": decision.status,
                "real_mutation_enabled": decision.real_mutation_enabled,
                "launch_ready": decision.launch_ready,
                "launch_allowed": decision.launch_allowed,
            }
            if decision.real_mutation_enabled or decision.launch_ready:
                errors.append("M026 decision unexpectedly enabled mutation or launch")
            if decision.status == "approve_m027_minimal_real_mutation_implementation":
                warnings.append("M027 implementation authorization only; launch remains disabled")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M026 decision unreadable: {exc}")
    if m027_authorization_path.exists():
        try:
            authorization = load_lambda_m027_authorization_record(m027_authorization_path)
            summary["m027_authorization"] = {
                "path": str(m027_authorization_path),
                "status": authorization.status,
                "real_mutation_enabled": authorization.real_mutation_enabled,
                "launch_ready": authorization.launch_ready,
                "launch_allowed": authorization.launch_allowed,
            }
            if authorization.real_mutation_enabled or authorization.launch_ready:
                errors.append("M027 authorization unexpectedly enabled mutation or launch")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M027 authorization unreadable: {exc}")
    if m026_blocker_matrix_path.exists():
        try:
            matrix = load_lambda_real_launch_blocker_matrix(m026_blocker_matrix_path)
            summary["m026_blocker_matrix"] = {
                "path": str(m026_blocker_matrix_path),
                "m027_authorization_blocked": matrix.m027_authorization_blocked,
                "real_launch_execution_blocked": matrix.real_launch_execution_blocked,
            }
            if matrix.real_launch_execution_blocked:
                warnings.append("M026 blocker matrix keeps real launch execution blocked")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M026 blocker matrix unreadable: {exc}")
    if m026_freshness_path.exists():
        try:
            freshness = load_lambda_evidence_freshness_report(m026_freshness_path)
            summary["m026_evidence_freshness"] = {
                "path": str(m026_freshness_path),
                "freshness_passed": freshness.freshness_passed,
                "stale_items": freshness.stale_items,
                "missing_items": freshness.missing_items,
            }
            if not freshness.freshness_passed:
                warnings.append("M026 evidence freshness requires more evidence")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M026 evidence freshness unreadable: {exc}")
    if m027_minimal_preflight_path.exists():
        try:
            minimal_preflight = load_lambda_minimal_mutation_preflight_report(
                m027_minimal_preflight_path
            )
            summary["m027_minimal_mutation_preflight"] = {
                "path": str(m027_minimal_preflight_path),
                "preflight_passed": minimal_preflight.preflight_passed,
                "fake_server_ready": minimal_preflight.fake_server_ready,
                "real_execution_allowed": minimal_preflight.real_execution_allowed,
                "launch_ready": minimal_preflight.launch_ready,
                "launch_allowed": minimal_preflight.launch_allowed,
            }
            if minimal_preflight.real_execution_allowed or minimal_preflight.launch_ready:
                errors.append("M027 minimal mutation preflight unexpectedly enabled execution")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M027 minimal mutation preflight unreadable: {exc}")
    if m027_minimal_audit_path.exists():
        try:
            minimal_audit = load_lambda_minimal_mutation_audit_report(
                m027_minimal_audit_path
            )
            summary["m027_minimal_mutation_audit"] = {
                "path": str(m027_minimal_audit_path),
                "audit_passed": minimal_audit.audit_passed,
                "real_lambda_api_used": minimal_audit.real_lambda_api_used,
                "real_mutating_operations": minimal_audit.real_mutating_operations,
                "billable_action_performed": minimal_audit.billable_action_performed,
            }
            if (
                minimal_audit.real_lambda_api_used
                or minimal_audit.real_mutating_operations
                or minimal_audit.billable_action_performed
            ):
                errors.append("M027 minimal mutation audit reported forbidden execution")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M027 minimal mutation audit unreadable: {exc}")
    if m029_authorization_path.exists():
        try:
            authorization = load_lambda_m029_authorization_package(m029_authorization_path)
            summary["m029_authorization"] = {
                "path": str(m029_authorization_path),
                "package_passed": authorization.package_passed,
                "authorized_for_next_milestone": (
                    authorization.launch_authorization.launch_authorized_for_next_milestone
                ),
                "launch_authorized_now": authorization.launch_authorization.launch_authorized_now,
                "launch_ready": authorization.launch_ready,
                "launch_allowed": authorization.launch_allowed,
            }
            if authorization.launch_authorization.launch_authorized_now:
                errors.append("M029 authorization unexpectedly authorized launch now")
            if authorization.package_passed:
                warnings.append("M029 authorization only; M028 build remains non-launchable")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M029 authorization package unreadable: {exc}")
    if m028_report_path.exists():
        try:
            report = load_lambda_m028_report(m028_report_path)
            summary["m028_report"] = {
                "path": str(m028_report_path),
                "report_passed": report.report_passed,
                "decision_status": report.decision_record.status,
                "launch_ready": report.launch_ready,
                "launch_allowed": report.launch_allowed,
            }
            if report.real_mutation_enabled or report.launch_ready or report.launch_allowed:
                errors.append("M028 report unexpectedly enabled launch or mutation")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda M028 report unreadable: {exc}")
    return {"summary": summary, "warnings": warnings, "errors": errors}
