import pytest

from decodilo.storage.fault_injection import (
    FaultInjectedArtifactBackend,
    FaultInjectionConfig,
    InjectedBackendCorruption,
    InjectedBackendFailure,
)
from decodilo.storage.local_backend import LocalFilesystemArtifactBackend
from decodilo.storage.retry_policy import RetryPolicy


def test_transient_read_failure_succeeds_with_retry(tmp_path) -> None:
    backend = LocalFilesystemArtifactBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="x", data=b"payload")
    wrapped = FaultInjectedArtifactBackend(
        backend,
        config=FaultInjectionConfig(transient_read_failures=1),
        retry_policy=RetryPolicy(
            max_attempts=2,
            retryable_error_types=(InjectedBackendFailure,),
        ),
    )

    assert wrapped.read_bytes(ref) == b"payload"
    assert wrapped.metrics.backend_retries == 1


def test_permanent_and_corrupt_reads_fail_closed(tmp_path) -> None:
    backend = LocalFilesystemArtifactBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="x", data=b"payload")

    permanent = FaultInjectedArtifactBackend(
        backend,
        config=FaultInjectionConfig(permanent_read_failure=True),
        retry_policy=RetryPolicy(
            max_attempts=2,
            retryable_error_types=(InjectedBackendFailure,),
        ),
    )
    with pytest.raises(InjectedBackendFailure):
        permanent.read_bytes(ref)

    corrupt = FaultInjectedArtifactBackend(
        backend,
        config=FaultInjectionConfig(corrupt_reads=1),
        retry_policy=RetryPolicy(max_attempts=1),
    )
    with pytest.raises(InjectedBackendCorruption):
        corrupt.read_bytes(ref)
    assert corrupt.metrics.backend_corruptions_detected == 1


def test_duplicate_write_is_idempotent_and_partial_write_does_not_commit(tmp_path) -> None:
    backend = LocalFilesystemArtifactBackend(tmp_path)
    first = backend.write_bytes(artifact_id="x", data=b"payload")
    second = backend.write_bytes(artifact_id="x", data=b"payload")
    assert first == second
    assert backend.list_refs() == [first]

    wrapped = FaultInjectedArtifactBackend(
        backend,
        config=FaultInjectionConfig(partial_write_failure=True),
    )
    with pytest.raises(InjectedBackendFailure):
        wrapped.write_bytes(artifact_id="bad", data=b"bad")
    assert all(ref.artifact_id != "bad" for ref in backend.list_refs())
