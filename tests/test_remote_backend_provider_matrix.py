import subprocess
import sys

import pytest

from decodilo.storage.remote_backend_provider_matrix import (
    ProviderCapabilityDeclaration,
    RemoteBackendProviderCandidate,
    build_provider_comparison_matrix,
)
from decodilo.storage.remote_backend_requirements import (
    RemoteBackendRequirementSet,
    write_remote_backend_requirements,
)


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m016-provider-matrix",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=5,
        peak_artifact_write_gbps=3,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=3,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def _candidate(
    name: str,
    *,
    conditional_put: bool,
    read_gbps: float,
) -> RemoteBackendProviderCandidate:
    return RemoteBackendProviderCandidate(
        provider_name=name,
        backend_type="manual_object_store",
        manual_capabilities=ProviderCapabilityDeclaration(
            read_gbps=read_gbps,
            write_gbps=4,
            ops_per_second=200,
            strong_read_after_write=True,
            monotonic_manifest_visibility=True,
            atomic_manifest_commit=True,
            conditional_put=conditional_put,
            encryption_at_rest=True,
            authentication=True,
            authorization_scopes=True,
            idempotent_put=True,
            idempotent_delete=True,
            lifecycle_delete=True,
            retention_policy=True,
            transaction_log=True,
            object_versioning=True,
        ),
    )


def test_provider_matrix_is_manual_only_and_scores_blockers() -> None:
    matrix = build_provider_comparison_matrix(
        requirements=_requirements(),
        providers=[
            _candidate("good-manual", conditional_put=True, read_gbps=8),
            _candidate("missing-conditional", conditional_put=False, read_gbps=8),
            _candidate("low-bandwidth", conditional_put=True, read_gbps=1),
        ],
    )

    by_name = {score.provider_name: score for score in matrix.scores}
    assert "missing conditional put" in by_name["missing-conditional"].blockers
    assert "insufficient read bandwidth" in by_name["low-bandwidth"].blockers
    assert matrix.remote_backend_enabled is False
    assert all(score.is_live_validated is False for score in matrix.scores)
    assert matrix.model_validate_json(matrix.to_json()) == matrix


def test_provider_candidate_rejects_live_validation() -> None:
    with pytest.raises(ValueError, match="live validated"):
        RemoteBackendProviderCandidate(
            provider_name="bad",
            backend_type="manual",
            manual_capabilities=ProviderCapabilityDeclaration(
                read_gbps=1,
                write_gbps=1,
                ops_per_second=1,
            ),
            is_live_validated=True,
        )


def test_provider_matrix_cli_runs(tmp_path) -> None:
    requirements_path = tmp_path / "requirements.json"
    providers_path = tmp_path / "providers.json"
    out_path = tmp_path / "provider-matrix.json"
    write_remote_backend_requirements(requirements_path, _requirements())
    providers_path.write_text(
        """
        {
          "providers": [
            {
              "provider_name": "manual",
              "backend_type": "manual_object_store",
              "manual_capabilities": {
                "read_gbps": 10,
                "write_gbps": 10,
                "ops_per_second": 1000,
                "conditional_put": true,
                "strong_read_after_write": true,
                "monotonic_manifest_visibility": true,
                "atomic_manifest_commit": true,
                "encryption_at_rest": true,
                "authentication": true,
                "authorization_scopes": true,
                "idempotent_put": true,
                "idempotent_delete": true,
                "lifecycle_delete": true,
                "retention_policy": true,
                "transaction_log": true,
                "object_versioning": true
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "provider-matrix",
            "--requirements",
            str(requirements_path),
            "--providers-json",
            str(providers_path),
            "--out",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert '"provider_count": 1' in result.stdout
    assert out_path.exists()
