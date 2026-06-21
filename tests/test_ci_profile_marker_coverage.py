from __future__ import annotations

from decodilo.runtime.ci_profile_manifest import CI_PROFILE_MARKERS, classify_test_file
from decodilo.runtime.ci_profile_report import build_ci_profile_report


def test_pytest_registers_all_ci_profile_markers(pytestconfig) -> None:
    configured = {
        marker.split(":", 1)[0].strip()
        for marker in pytestconfig.getini("markers")
    }

    assert set(CI_PROFILE_MARKERS) <= configured


def test_static_classifier_marks_lambda_tests_offline() -> None:
    markers = classify_test_file("tests/test_lambda_mutation_guard.py")

    assert "lambda_offline" in markers
    assert "cloud" in markers
    assert "lambda_live" not in markers
    assert "lambda_real_mutation" not in markers


def test_static_classifier_marks_representative_quick_tests() -> None:
    markers = classify_test_file("tests/test_cloud_still_disabled_m047.py")

    assert "quick" in markers
    assert "lambda_offline" in markers
    assert "subprocess_heavy" not in markers
    assert "lambda_live" not in markers


def test_static_classifier_marks_subprocess_heavy_runtime_tests() -> None:
    markers = classify_test_file("tests/test_local_process_failure.py")

    assert "runtime_local" in markers
    assert "subprocess_heavy" in markers


def test_quick_classifier_never_marks_real_lambda_profiles() -> None:
    quick_files = [
        "tests/test_lambda_no_live_calls_in_tests.py",
        "tests/test_ci_profile_quick_smoke.py",
        "tests/test_lambda_capacity_selected_execution_gate_check.py",
    ]
    for path in quick_files:
        markers = classify_test_file(path)
        assert "quick" in markers
        assert "lambda_live" not in markers
        assert "lambda_real_mutation" not in markers
        assert "subprocess_heavy" not in markers


def test_ci_profile_report_has_no_unmarked_tests_or_conflicts() -> None:
    report = build_ci_profile_report()

    assert report.unmarked_test_count == 0
    assert report.unmarked_test_files == []
    assert report.unmarked_test_nodeids == []
    assert report.suspected_marker_conflicts == []
    assert report.conflicting_profile_tests == []


def test_ci_profile_report_keeps_quick_small_and_safe() -> None:
    report = build_ci_profile_report()
    quick_nodeids = set(report.tests_by_profile["quick"])
    forbidden_profiles = {
        "lambda_live",
        "lambda_real_mutation",
        "subprocess_heavy",
        "launch_history_heavy",
    }

    assert report.quick_profile_count < 75
    for profile in forbidden_profiles:
        assert quick_nodeids.isdisjoint(report.tests_by_profile.get(profile, []))
