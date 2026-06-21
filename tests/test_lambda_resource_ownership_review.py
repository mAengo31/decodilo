from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.mutation_resource_scope import (
    LambdaMutationResourceScope,
    LambdaOwnedResourceScope,
)
from decodilo.lambda_cloud.resource_ownership_review import (
    review_lambda_resource_ownership,
)


def test_resource_ownership_review_clean_scope_passes(tmp_path):
    paths = write_m024_prepare_inputs(tmp_path)
    review = review_lambda_resource_ownership(
        m020_report=paths["m020"],
        resource_scope=paths["scope"],
    )

    assert review.resource_ownership_passed is True
    assert review.terminate_unowned_allowed is False
    assert review.launch_allowed is False


def test_resource_ownership_review_blocks_unowned_resource_scope(tmp_path):
    paths = write_m024_prepare_inputs(tmp_path)
    scope = LambdaMutationResourceScope(
        run_id="run",
        owned_scope=LambdaOwnedResourceScope(owned_resource_ids=["planned-owned-placeholder"]),
        unowned_live_resource_ids=["live-i-unowned"],
    )
    review = review_lambda_resource_ownership(m020_report=paths["m020"], resource_scope=scope)

    assert review.resource_ownership_passed is False
    assert any("unowned" in blocker for blocker in review.blockers)
