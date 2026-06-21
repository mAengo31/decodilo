from __future__ import annotations

from decodilo.runtime.ci_profile_manifest import (
    CI_PROFILE_MARKERS,
    QUICK_EXPRESSION,
    build_ci_profile_manifest,
)


def test_ci_profile_manifest_defines_required_profiles() -> None:
    manifest = build_ci_profile_manifest()
    profiles = manifest.by_name()

    assert {
        "unit",
        "quick",
        "lambda_offline",
        "runtime_local",
        "lifecycle",
        "perf",
        "torch_optional",
        "full",
        "live_readonly_manual",
        "real_mutation_manual",
    } <= set(profiles)
    assert set(CI_PROFILE_MARKERS) <= set(manifest.markers)


def test_quick_profile_excludes_live_mutation_and_subprocess_heavy_tests() -> None:
    manifest = build_ci_profile_manifest()
    quick = manifest.by_name()["quick"]

    assert quick.marker_expression == QUICK_EXPRESSION
    assert "quick" in quick.marker_expression
    assert "not lambda_live" in quick.marker_expression
    assert "not lambda_real_mutation" in quick.marker_expression
    assert "not subprocess_heavy" in quick.marker_expression
    assert "not launch_history_heavy" in quick.marker_expression
    assert quick.target_seconds == 60.0


def test_manual_profiles_are_never_default_launch_profiles() -> None:
    manifest = build_ci_profile_manifest()
    profiles = manifest.by_name()

    assert profiles["live_readonly_manual"].manual_only is True
    assert profiles["real_mutation_manual"].manual_only is True
    assert manifest.launch_ready is False
    assert manifest.launch_allowed is False
    assert manifest.billable_action_performed is False
    assert manifest.real_mutation_enabled is False
