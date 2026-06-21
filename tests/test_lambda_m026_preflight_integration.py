from lambda_m026_helpers import write_m026_core_artifacts

from decodilo.cloud.lambda_api_preflight import collect_lambda_api_preflight_evidence
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_preflight_includes_m026_decision_without_enabling_launch(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)

    report = run_lambda_preflight(
        m026_decision_record=paths["decision"],
        m027_authorization_record=paths["authorization"],
        m026_blocker_matrix=paths["blocker_matrix"],
        m026_evidence_freshness=paths["freshness"],
    )

    assert report.m026_decision_summary is not None
    assert (
        report.m026_decision_summary["decision_status"]
        == "approve_m027_minimal_real_mutation_implementation"
    )
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert any("M027 implementation authorization only" in item for item in report.warnings)


def test_lambda_api_preflight_collector_includes_m026_artifacts(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)
    copies = {
        "decision": "lambda-m026-decision.json",
        "authorization": "lambda-m027-authorization.json",
        "blocker_matrix": "lambda-blocker-matrix.json",
        "freshness": "lambda-evidence-freshness.json",
    }
    for key, name in copies.items():
        (tmp_path / name).write_text(paths[key].read_text(encoding="utf-8"), encoding="utf-8")

    evidence = collect_lambda_api_preflight_evidence(root=tmp_path)
    summary = evidence["summary"]

    assert summary["m026_decision"]["status"] == (
        "approve_m027_minimal_real_mutation_implementation"
    )
    assert summary["m027_authorization"]["launch_allowed"] is False
    assert summary["m026_blocker_matrix"]["real_launch_execution_blocked"] is True
    assert summary["m026_evidence_freshness"]["freshness_passed"] is True
