from __future__ import annotations

from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    LambdaM087RParameterFragmentAuthorization,
    write_lambda_m087r_parameter_fragment_authorization,
)
from decodilo.lambda_cloud.m087r_parameter_fragment_runbook_preview import (
    build_lambda_m087r_parameter_fragment_runbook_preview_from_path,
)


def test_m087r_runbook_preview_blocks_without_safe_command(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m087r_parameter_fragment_authorization(
        authorization_path,
        LambdaM087RParameterFragmentAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_parameter_fragment_command_found"],
        ),
    )

    preview = build_lambda_m087r_parameter_fragment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "blocked_no_safe_parameter_fragment_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m087r_runbook_preview_ready_but_non_executable_when_authorized(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m087r_parameter_fragment_authorization(
        authorization_path,
        LambdaM087RParameterFragmentAuthorization(
            authorization_status=(
                "authorized_for_future_m087r_parameter_fragment_smoke"
            ),
            expected_parameter_fragment_semantics="synthetic_vector_fragments",
        ),
    )

    preview = build_lambda_m087r_parameter_fragment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "ready_for_future_m087r_parameter_fragment_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
    assert preview.billable_action_performed is False
    assert any("synthetic_vector_fragments" in item for item in preview.future_requirements)
