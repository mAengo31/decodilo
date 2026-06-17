import pytest

from decodilo.syncer.global_manifest_lifecycle import (
    GlobalStateLifecyclePolicy,
    GlobalStateManifest,
    plan_global_state_lifecycle,
)

pytestmark = pytest.mark.unit


def test_latest_checkpoint_and_snapshot_states_are_protected() -> None:
    manifest = GlobalStateManifest(
        run_id="run-global",
        latest_version=5,
        versions={version: {"path": f"global-{version}.artifact.json"} for version in range(6)},
    )
    report = plan_global_state_lifecycle(
        manifest,
        GlobalStateLifecyclePolicy(
            keep_latest_global_states=1,
            checkpoint_referenced_versions={2},
            snapshot_referenced_versions={3},
        ),
    )

    assert 5 in report.protected_versions
    assert 2 in report.protected_versions
    assert 3 in report.protected_versions
    assert 0 in report.eligible_versions

