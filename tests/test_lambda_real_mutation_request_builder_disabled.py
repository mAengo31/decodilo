from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.real_mutation_request_builder import (
    LambdaRealMutationRequestBuilder,
)


def test_request_builder_complete_evidence_produces_review_only_plan(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)

    result = LambdaRealMutationRequestBuilder().build_review_plan(
        operation_name="launch_one_instance",
        operation_spec=refs["operation"],
        budget_lock=refs["budget"],
        idempotency_plan=refs["idempotency"],
        resource_scope=refs["scope"],
    )

    assert result.build_status == "review_plan_built"
    assert result.endpoint_template_metadata
    assert result.executable_url is None
    assert result.executable_body is None
    assert result.request_body_present is False
    assert result.launch_allowed is False


def test_request_builder_missing_evidence_blocks(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)

    result = LambdaRealMutationRequestBuilder().build_review_plan(
        operation_name="launch_one_instance",
        operation_spec=refs["operation"],
        budget_lock=None,
        idempotency_plan=refs["idempotency"],
        resource_scope=refs["scope"],
    )

    assert result.build_status == "blocked"
    assert "missing evidence: budget_lock" in result.errors
    assert result.executable_url is None


def test_request_builder_rejects_read_operation_as_mutation_plan(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)

    result = LambdaRealMutationRequestBuilder().build_review_plan(
        operation_name="list_instances_read_only",
        operation_spec=refs["operation"],
        budget_lock=refs["budget"],
        idempotency_plan=refs["idempotency"],
        resource_scope=refs["scope"],
    )

    assert result.build_status == "blocked"
    assert any("future_mutation_operation" in error for error in result.errors)
