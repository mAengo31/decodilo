from lambda_m025_helpers import write_m025_core_artifacts
from pydantic import ValidationError

from decodilo.lambda_cloud.go_no_go_record import (
    LambdaGoNoGoRecord,
    build_lambda_go_no_go_record,
)


def test_clean_review_reaches_future_m026_review_only(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    record = build_lambda_go_no_go_record(review=paths["review"])

    assert record.status == "go_for_future_m026_real_launch_review"
    assert record.launch_allowed is False


def test_forbidden_go_no_go_status_rejected():
    try:
        LambdaGoNoGoRecord(
            final_prelaunch_review_ref="review",
            status="launch_allowed",  # type: ignore[arg-type]
            rationale="bad",
        )
    except ValidationError:
        return
    raise AssertionError("expected forbidden status to be rejected")
