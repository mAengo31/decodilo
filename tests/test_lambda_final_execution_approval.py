from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.final_execution_approval import (
    build_lambda_final_execution_approval,
)
from decodilo.lambda_cloud.m028_decision_record import load_lambda_m028_decision_record
from decodilo.lambda_cloud.m029_launch_authorization import (
    load_lambda_m029_authorization_package,
)


def test_final_execution_approval_is_next_milestone_only(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)
    approval = build_lambda_final_execution_approval(
        decision_record=load_lambda_m028_decision_record(paths["m028_decision"]),
        m029_authorization=load_lambda_m029_authorization_package(
            paths["m029_authorization"]
        ),
    )

    assert approval.approved_for_next_milestone_only is True
    assert approval.launch_allowed is False

