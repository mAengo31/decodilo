import pytest

from decodilo.storage.remote_backend_evidence import build_remote_backend_evidence_package
from decodilo.storage.remote_backend_proposal import (
    build_remote_backend_implementation_proposal,
)
from decodilo.storage.remote_backend_provider_matrix import (
    ProviderCapabilityDeclaration,
    RemoteBackendProviderCandidate,
    build_provider_comparison_matrix,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m017-proposal",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=7.168,
        peak_artifact_write_gbps=3.808,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=3.808,
        checkpoint_storage_growth_gb_per_hour=2,
        event_log_growth_mb_per_hour=10,
        required_replay_snapshot_frequency="every checkpoint",
    )


def _matrix(requirements: RemoteBackendRequirementSet):
    provider = RemoteBackendProviderCandidate(
        provider_name="manual-simulated",
        backend_type="manual_object_store",
        manual_capabilities=ProviderCapabilityDeclaration(
            read_gbps=10,
            write_gbps=5,
            ops_per_second=1000,
            conditional_put=True,
            encryption_at_rest=True,
            authentication=True,
            authorization_scopes=True,
            idempotent_put=True,
            idempotent_delete=True,
            lifecycle_delete=True,
            transaction_log=True,
            object_versioning=True,
        ),
    )
    return build_provider_comparison_matrix(requirements=requirements, providers=[provider])


def test_proposal_builds_from_complete_evidence(tmp_path) -> None:
    requirements = _requirements()
    evidence_file = tmp_path / "evidence-source.json"
    evidence_file.write_text('{"ok": true}\n', encoding="utf-8")
    evidence = build_remote_backend_evidence_package(
        evidence_paths={"source": evidence_file}
    )

    proposal = build_remote_backend_implementation_proposal(
        requirements=requirements,
        evidence_package=evidence,
        provider_matrix=_matrix(requirements),
        provider_name="manual-simulated",
        readiness_report_ref="readiness.json",
        evidence_package_ref="evidence.json",
        conformance_report_ref="conformance.json",
        requirement_ref="requirements.json",
        provider_matrix_ref="provider-matrix.json",
        proposed_sdk_name="future-object-sdk",
        proposed_sdk_version_constraint=">=1.0",
    )

    assert proposal.blockers == []
    assert proposal.explicit_non_goals.no_cloud_launch is True
    assert proposal.dependency_plan.dependency_addition_allowed is False
    assert proposal.remote_backend_enabled is False
    assert proposal.launch_allowed is False
    assert proposal.model_validate_json(proposal.to_json()) == proposal


def test_proposal_warns_or_blocks_on_missing_evidence(tmp_path) -> None:
    requirements = _requirements()
    evidence = build_remote_backend_evidence_package(
        evidence_paths={"missing": tmp_path / "missing.json"}
    )

    proposal = build_remote_backend_implementation_proposal(
        requirements=requirements,
        evidence_package=evidence,
        provider_matrix=_matrix(requirements),
        provider_name="manual-simulated",
        readiness_report_ref="readiness.json",
        evidence_package_ref="evidence.json",
        conformance_report_ref="conformance.json",
        requirement_ref="requirements.json",
    )

    assert "evidence package incomplete" in proposal.blockers


def test_proposal_rejects_raw_secret_like_sdk_metadata(tmp_path) -> None:
    requirements = _requirements()
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    evidence = build_remote_backend_evidence_package(evidence_paths={"source": source})

    with pytest.raises(ValueError, match="secret-like"):
        build_remote_backend_implementation_proposal(
            requirements=requirements,
            evidence_package=evidence,
            provider_matrix=_matrix(requirements),
            provider_name="manual-simulated",
            readiness_report_ref="readiness.json",
            evidence_package_ref="evidence.json",
            conformance_report_ref="conformance.json",
            requirement_ref="requirements.json",
            proposed_sdk_name="AKIA1234567890123456",
        )
