from decodilo.storage.remote_backend_idempotency_model import (
    RemoteBackendIdempotencyPolicy,
    evaluate_remote_backend_idempotency,
)


def test_idempotency_policy_passes_by_default() -> None:
    assert evaluate_remote_backend_idempotency(RemoteBackendIdempotencyPolicy()).passed is True


def test_missing_conditional_put_creates_blocker() -> None:
    report = evaluate_remote_backend_idempotency(
        RemoteBackendIdempotencyPolicy(conditional_manifest_commit_required=False)
    )

    assert report.passed is False
    assert "conditional manifest commit is required" in report.errors


def test_short_duplicate_window_warns() -> None:
    report = evaluate_remote_backend_idempotency(
        RemoteBackendIdempotencyPolicy(duplicate_suppression_window_seconds=10)
    )

    assert report.passed is True
    assert report.warnings
