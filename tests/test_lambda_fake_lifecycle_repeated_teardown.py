from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def test_repeated_fake_teardown_remains_idempotent(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    launch = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    path = tmp_path / "life" / "report.json"
    path.write_text(launch.to_json(), encoding="utf-8")
    first = execute_fake_lambda_teardown(lifecycle_report_path=path)
    path.write_text(first.to_json(), encoding="utf-8")
    second = execute_fake_lambda_teardown(lifecycle_report_path=path)

    assert first.fake_resources_terminated == second.fake_resources_terminated == 1
    assert second.manual_review_required is False
