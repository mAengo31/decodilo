from lambda_fake_lifecycle_helpers import write_approved_m020, write_incomplete_approval

from decodilo.lambda_cloud.fake_lifecycle_preflight import (
    run_fake_lambda_lifecycle_preflight,
)


def test_fake_lifecycle_preflight_passes_with_complete_fake_approval(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)

    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=approval_path,
    )

    assert preflight.passed is True
    assert preflight.fake_lifecycle_only is True
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False


def test_fake_lifecycle_preflight_fails_missing_m020(tmp_path) -> None:
    approval_path = write_incomplete_approval(tmp_path)

    try:
        run_fake_lambda_lifecycle_preflight(
            m020_report=tmp_path / "missing.json",
            approval_manifest=approval_path,
        )
    except FileNotFoundError:
        failed = True
    else:
        failed = False

    assert failed is True


def test_fake_lifecycle_preflight_fails_real_launch_style_approval(tmp_path) -> None:
    _report, m020_path, _approval_path = write_approved_m020(tmp_path)
    incomplete = write_incomplete_approval(tmp_path)

    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=incomplete,
    )

    assert preflight.passed is False
    assert any("approved_for_future_fake" in error for error in preflight.errors)


def test_fake_lifecycle_preflight_fails_over_budget(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(
        tmp_path,
        max_run_budget=5,
    )

    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=approval_path,
    )

    assert preflight.passed is False
    assert any("price reconciliation" in error for error in preflight.errors)
