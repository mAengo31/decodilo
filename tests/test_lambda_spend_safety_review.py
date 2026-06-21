from lambda_fake_lifecycle_helpers import write_approved_m020
from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.spend_safety_review import review_lambda_spend_safety


def test_spend_safety_review_valid_case_passes(tmp_path):
    paths = write_m024_prepare_inputs(tmp_path)
    review = review_lambda_spend_safety(
        m020_report=paths["m020"],
        budget_lock=paths["budget"],
    )

    assert review.spend_safety_passed is True
    assert review.max_budget <= 50
    assert review.launch_allowed is False


def test_spend_safety_review_blocks_budget_over_50(tmp_path):
    _report, m020, _approval = write_approved_m020(tmp_path, max_run_budget=60)
    review = review_lambda_spend_safety(m020_report=m020)

    assert review.spend_safety_passed is False
    assert any("50" in blocker for blocker in review.blockers)
