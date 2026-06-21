import pytest
from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.disabled_real_mutation_transport import (
    LambdaRealMutationDisabledError,
)
from decodilo.lambda_cloud.real_mutation_skeleton_client import (
    LambdaRealMutationSkeletonClient,
)


def test_prepare_launch_produces_review_only_plan(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)
    result = LambdaRealMutationSkeletonClient().prepare_launch_one_instance(
        operation_spec=refs["operation"],
        budget_lock=refs["budget"],
        idempotency_plan=refs["idempotency"],
        resource_scope=refs["scope"],
    )

    assert result.build_status == "review_plan_built"
    assert result.real_request_allowed is False
    assert result.launch_allowed is False


def test_skeleton_launch_and_terminate_raise_before_request_construction() -> None:
    client = LambdaRealMutationSkeletonClient()

    with pytest.raises(LambdaRealMutationDisabledError) as launch_error:
        client.launch_one_instance()
    with pytest.raises(LambdaRealMutationDisabledError) as terminate_error:
        client.terminate_owned_instance()

    assert launch_error.value.report.request_constructed is False
    assert terminate_error.value.report.request_body_constructed is False


def test_feature_flags_cannot_enable_skeleton_execution() -> None:
    report = LambdaRealMutationSkeletonClient().evaluate_guard_for_review()

    assert report.review_only_passed is True
    assert report.execution_guard_passed_for_execution is False
    assert report.launch_allowed is False
