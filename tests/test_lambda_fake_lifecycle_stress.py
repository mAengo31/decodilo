from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_lifecycle_stress import run_fake_lambda_lifecycle_stress


def test_short_fake_lifecycle_stress_run_passes(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)

    stress = run_fake_lambda_lifecycle_stress(
        m020_report=m020_path,
        approval_manifest=approval_path,
        workdir=tmp_path / "stress",
        cycles=2,
        failure_modes=["none"],
    )

    assert stress.cycles_completed == 2
    assert stress.cycles_failed == 0
    assert stress.journal_replay_passed is True
    assert stress.teardown_verification_passed is True
    assert stress.mutation_contract_passed is True
    assert stress.launch_allowed is False


def test_fake_lifecycle_stress_with_partial_failure_reports_manual_review(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)

    stress = run_fake_lambda_lifecycle_stress(
        m020_report=m020_path,
        approval_manifest=approval_path,
        workdir=tmp_path / "stress",
        cycles=1,
        failure_modes=["partial_terminate_failure"],
    )

    assert stress.cycles_completed == 1
    assert stress.cycles_failed == 1
    assert stress.manual_review_required is True
    assert stress.fake_orphans_detected == 1


def test_fake_lifecycle_stress_report_schema_validates(tmp_path) -> None:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    stress = run_fake_lambda_lifecycle_stress(
        m020_report=m020_path,
        approval_manifest=approval_path,
        workdir=tmp_path / "stress",
        cycles=1,
        failure_modes=["none"],
    )

    assert "cycles_requested" in stress.to_json()
    assert stress.billable_action_performed is False
