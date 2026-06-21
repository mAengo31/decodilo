from lambda_m026_helpers import write_m026_core_artifacts

from decodilo.lambda_cloud.m026_report import build_lambda_m026_report
from decodilo.lambda_cloud.m027_authorization_record import (
    load_lambda_m027_authorization_record,
)
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    load_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_record import (
    load_lambda_real_launch_decision_record,
)


def test_m026_report_builds_with_approved_m027_authorization(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)
    decision = load_lambda_real_launch_decision_record(paths["decision"])
    authorization = load_lambda_m027_authorization_record(paths["authorization"])
    matrix = load_lambda_real_launch_blocker_matrix(paths["blocker_matrix"])

    report = build_lambda_m026_report(
        decision_record=decision,
        authorization_record=authorization,
        blocker_matrix=matrix,
    )

    assert report.decision_record.status == "approve_m027_minimal_real_mutation_implementation"
    assert (
        report.m027_authorization_record.status
        == "authorized_to_implement_minimal_mutation_code_disabled_by_default"
    )
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
