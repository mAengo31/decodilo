import pytest
from lambda_m036_helpers import support_response

from decodilo.lambda_cloud.ambiguous_response_semantics import (
    build_lambda_ambiguous_response_semantics,
)


def test_ambiguous_launch_semantics_require_manual_review_trigger():
    report = build_lambda_ambiguous_response_semantics(support_response())

    assert report.launch_timeout_may_create_instance is True
    assert report.manual_review_trigger_required is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ambiguous_launch_behavior_is_required():
    with pytest.raises(ValueError, match="ambiguous launch behavior"):
        build_lambda_ambiguous_response_semantics(
            support_response(missing=("launch_timeout_may_create",))
        )

