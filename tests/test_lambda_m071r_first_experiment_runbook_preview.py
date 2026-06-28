from __future__ import annotations

from decodilo.lambda_cloud.m071r_first_experiment_authorization import (
    LambdaM071RFirstExperimentAuthorization,
    write_lambda_m071r_first_experiment_authorization,
)
from decodilo.lambda_cloud.m071r_first_experiment_runbook_preview import (
    build_lambda_m071r_first_experiment_runbook_preview_from_path,
)


def test_m071r_runbook_preview_is_non_executable(tmp_path):
    auth = tmp_path / "auth.json"
    write_lambda_m071r_first_experiment_authorization(
        auth,
        LambdaM071RFirstExperimentAuthorization(
            authorization_status="authorized_for_future_m071r_first_experiment_attempt",
        ),
    )

    preview = build_lambda_m071r_first_experiment_runbook_preview_from_path(
        authorization=auth,
    )

    assert preview.preview_status == "ready_for_future_m071r_first_experiment_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
