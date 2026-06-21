import pytest

from decodilo.storage.remote_backend_decision_record import (
    RemoteBackendDecisionRecord,
    RemoteBackendDecisionStatus,
    build_remote_backend_decision_record,
)
from decodilo.storage.remote_backend_risk_register import (
    RemoteBackendRiskRegister,
    build_default_remote_backend_risk_register,
)
from decodilo.storage.remote_backend_sdk_guard import RemoteBackendSDKGuardReport


def _guard(passed: bool = True) -> RemoteBackendSDKGuardReport:
    return RemoteBackendSDKGuardReport(
        passed=passed,
        project_root=".",
        errors=[] if passed else ["forbidden dependency: boto3"],
    )


def _empty_risks() -> RemoteBackendRiskRegister:
    return RemoteBackendRiskRegister(risks=[])


def test_missing_evidence_needs_more_evidence() -> None:
    record = build_remote_backend_decision_record(
        proposal_ref="proposal.json",
        evidence_package_ref="evidence.json",
        readiness_report_ref="readiness.json",
        risk_register_ref="risk.json",
        sdk_guard_report_ref="guard.json",
        sdk_guard_report=_guard(),
        risk_register=_empty_risks(),
        evidence_complete=False,
    )

    assert record.status == RemoteBackendDecisionStatus.needs_more_evidence
    assert record.launch_allowed is False


def test_sdk_guard_failure_blocks() -> None:
    record = build_remote_backend_decision_record(
        proposal_ref="proposal.json",
        evidence_package_ref="evidence.json",
        readiness_report_ref="readiness.json",
        risk_register_ref="risk.json",
        sdk_guard_report_ref="guard.json",
        sdk_guard_report=_guard(False),
        risk_register=_empty_risks(),
    )

    assert record.status == RemoteBackendDecisionStatus.blocked_by_missing_capability
    assert record.blockers


def test_critical_risk_blocks() -> None:
    record = build_remote_backend_decision_record(
        proposal_ref="proposal.json",
        evidence_package_ref="evidence.json",
        readiness_report_ref="readiness.json",
        risk_register_ref="risk.json",
        sdk_guard_report_ref="guard.json",
        sdk_guard_report=_guard(),
        risk_register=build_default_remote_backend_risk_register(),
    )

    assert record.status == RemoteBackendDecisionStatus.blocked_by_risk


def test_complete_simulator_evidence_is_future_review_candidate_only() -> None:
    record = build_remote_backend_decision_record(
        proposal_ref="proposal.json",
        evidence_package_ref="evidence.json",
        readiness_report_ref="readiness.json",
        risk_register_ref="risk.json",
        sdk_guard_report_ref="guard.json",
        sdk_guard_report=_guard(),
        risk_register=_empty_risks(),
    )

    assert record.status == RemoteBackendDecisionStatus.candidate_for_future_sdk_review
    assert record.remote_backend_enabled is False
    assert record.launch_ready is False


def test_forbidden_decision_status_rejected() -> None:
    with pytest.raises(ValueError, match="cannot allow SDK addition"):
        RemoteBackendDecisionRecord(
            decision_id="bad",
            proposal_ref="proposal.json",
            evidence_package_ref="evidence.json",
            readiness_report_ref="readiness.json",
            risk_register_ref="risk.json",
            sdk_guard_report_ref="guard.json",
            status=RemoteBackendDecisionStatus.sdk_addition_allowed_by_policy,
            rationale="bad",
        )
