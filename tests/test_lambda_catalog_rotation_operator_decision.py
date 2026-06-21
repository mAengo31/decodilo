from pathlib import Path

from decodilo.lambda_cloud.catalog_rotation_operator_decision import (
    build_lambda_catalog_rotation_operator_decision_from_path,
)
from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    build_lambda_catalog_rotation_risk_acceptance,
)


def _write(tmp_path: Path, report) -> Path:
    path = tmp_path / "risk.json"
    path.write_text(report.to_json(), encoding="utf-8")
    return path


def test_catalog_rotation_operator_decision_accept(tmp_path):
    path = _write(
        tmp_path,
        build_lambda_catalog_rotation_risk_acceptance(
            accept_selected_candidate=True,
            acknowledge_all=True,
        ),
    )
    report = build_lambda_catalog_rotation_operator_decision_from_path(path)

    assert report.decision_status == "accept_selected_catalog_rotation_candidate"
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"


def test_catalog_rotation_operator_decision_wait(tmp_path):
    path = _write(
        tmp_path,
        build_lambda_catalog_rotation_risk_acceptance(decline_wait=True),
    )
    report = build_lambda_catalog_rotation_operator_decision_from_path(path)

    assert report.decision_status == "wait_for_live_availability"


def test_catalog_rotation_operator_decision_manual(tmp_path):
    path = _write(
        tmp_path,
        build_lambda_catalog_rotation_risk_acceptance(decline_manual_selection=True),
    )
    report = build_lambda_catalog_rotation_operator_decision_from_path(path)

    assert report.decision_status == "require_manual_candidate_selection"


def test_catalog_rotation_operator_decision_incomplete(tmp_path):
    path = _write(tmp_path, build_lambda_catalog_rotation_risk_acceptance())
    report = build_lambda_catalog_rotation_operator_decision_from_path(path)

    assert report.decision_status == "incomplete"
    assert "catalog_rotation_operator_decision_not_provided" in report.blockers
