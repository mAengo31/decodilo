from decodilo.cloud.remote_backend_review_preflight import (
    collect_remote_backend_review_preflight,
)
from decodilo.storage.remote_backend_decision_record import (
    build_remote_backend_decision_record,
    write_remote_backend_decision_record,
)
from decodilo.storage.remote_backend_risk_register import (
    RemoteBackendRiskRegister,
    write_remote_backend_risk_register,
)
from decodilo.storage.remote_backend_sdk_guard import (
    RemoteBackendSDKGuardReport,
    write_remote_backend_sdk_guard_report,
)


def test_review_preflight_warns_when_review_package_missing(tmp_path) -> None:
    result = collect_remote_backend_review_preflight(root=tmp_path)

    assert "remote backend review package missing" in result["warnings"]
    assert result["summary"]["remote_backend_enabled"] is False
    assert result["summary"]["launch_allowed"] is False


def test_review_preflight_includes_candidate_decision_status(tmp_path) -> None:
    guard = RemoteBackendSDKGuardReport(passed=True, project_root=".")
    risks = RemoteBackendRiskRegister(risks=[])
    decision = build_remote_backend_decision_record(
        proposal_ref="remote-proposal.json",
        evidence_package_ref="evidence-package.json",
        readiness_report_ref="readiness.json",
        risk_register_ref="risk-register.json",
        sdk_guard_report_ref="sdk-guard.json",
        sdk_guard_report=guard,
        risk_register=risks,
    )
    write_remote_backend_decision_record(tmp_path / "decision-record.json", decision)
    write_remote_backend_sdk_guard_report(tmp_path / "sdk-guard.json", guard)
    write_remote_backend_risk_register(tmp_path / "risk-register.json", risks)
    (tmp_path / "remote-proposal.json").write_text(
        '{"provider_candidate_name":"manual"}\n',
        encoding="utf-8",
    )

    result = collect_remote_backend_review_preflight(root=tmp_path)

    assert result["summary"]["decision_status"] == "candidate_for_future_sdk_review"
    assert "future SDK review candidate only; backend remains disabled" in result["warnings"]
    assert result["summary"]["remote_backend_enabled"] is False
