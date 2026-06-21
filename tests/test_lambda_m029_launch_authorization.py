from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029LaunchAuthorization,
    build_lambda_m029_authorization_package,
)


def test_m029_authorization_builds_from_complete_evidence(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    package = build_lambda_m029_authorization_package(
        state_snapshot=paths["snapshot"],
        budget_lock=paths["budget"],
        resource_lock=paths["resource"],
        launch_window_lock=paths["window"],
        teardown_plan=paths["final_teardown"],
        operator_confirmation=paths["operator"],
        no_mutation_audit=paths["no_mutation"],
    )

    assert package.package_passed is True
    assert package.launch_authorization.launch_authorized_for_next_milestone is True
    assert package.launch_authorization.launch_authorized_now is False
    assert package.launch_allowed is False


def test_forbidden_operation_cannot_be_authorized():
    try:
        LambdaM029LaunchAuthorization(
            authorization_id="auth",
            authorized_operations=["restart"],
            planned_instance_type="gpu_8x_h100_sxm",
            planned_region="us-west-1",
            idempotency_plan_hash="idem",
            budget_lock_hash="budget",
            resource_lock_hash="resource",
            launch_window_lock_hash="window",
            teardown_plan_hash="teardown",
            operator_confirmation_hash="operator",
        )
    except ValueError as exc:
        assert "forbidden operation" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("forbidden operation should be rejected")

