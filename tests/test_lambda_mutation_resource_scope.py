from lambda_m024_helpers import write_m024_prepare_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.mutation_resource_scope import (
    LambdaMutationResourceScope,
    LambdaOwnedResourceScope,
    build_lambda_mutation_resource_scope,
    evaluate_lambda_mutation_resource_scope,
)


def test_owned_placeholder_accepted_for_review(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)
    scope = build_lambda_mutation_resource_scope(m020_report=refs["m020"])
    report = evaluate_lambda_mutation_resource_scope(scope)

    assert scope.owned_scope.scope_id == "planned-owned-placeholder"
    assert report.scope_valid_for_review is True
    assert report.scope_valid_for_execution is False
    assert scope.launch_allowed is False


def test_unowned_live_instance_rejected_from_owned_scope() -> None:
    try:
        LambdaMutationResourceScope(
            run_id="run",
            owned_scope=LambdaOwnedResourceScope(owned_resource_ids=["i-live"]),
            unowned_live_resource_ids=["i-live"],
        )
    except ValidationError as exc:
        assert "unowned live resources" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unowned live resource accepted")


def test_terminate_unowned_rejected() -> None:
    try:
        LambdaMutationResourceScope(run_id="run", terminate_unowned_allowed=True)
    except ValidationError as exc:
        assert "terminate_unowned" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("terminate_unowned accepted")
