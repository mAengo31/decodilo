from decodilo.storage.remote_backend_replay_restore_model import (
    RemoteBackendReplayRestorePolicy,
    evaluate_remote_backend_replay_restore,
)


def test_replay_restore_policy_passes_by_default() -> None:
    assert evaluate_remote_backend_replay_restore(RemoteBackendReplayRestorePolicy()).passed is True


def test_stale_object_protection_required() -> None:
    report = evaluate_remote_backend_replay_restore(
        RemoteBackendReplayRestorePolicy(stale_object_protection_required=False)
    )

    assert report.passed is False
    assert any("stale_object_protection_required" in error for error in report.errors)
