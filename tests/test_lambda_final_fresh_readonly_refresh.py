from decodilo.lambda_cloud.final_fresh_readonly_refresh import (
    LambdaFinalFreshReadOnlyRefreshReport,
    build_lambda_refresh_not_run_report,
)


def test_missing_env_refresh_report_keeps_flags_false():
    report = build_lambda_refresh_not_run_report(status="not_run_no_env")

    assert report.refresh_status == "not_run_no_env"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_read_only_violation_rejected():
    try:
        LambdaFinalFreshReadOnlyRefreshReport(
            refresh_status="run_read_only_failed",
            mutating_operations=1,
        )
    except ValueError as exc:
        assert "mutating operations" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("mutating refresh report should be rejected")

