from decodilo.storage.remote_backend_provider_assessment import (
    assess_remote_backend_provider,
)
from decodilo.storage.remote_backend_provider_matrix import (
    ProviderCapabilityDeclaration,
    RemoteBackendProviderCandidate,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m017-assessment",
        target_learner_count=4,
        stress_learner_count=8,
        peak_artifact_read_gbps=5,
        peak_artifact_write_gbps=3,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=2,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def _provider(name: str, *, read_gbps: float, conditional_put: bool):
    return RemoteBackendProviderCandidate(
        provider_name=name,
        backend_type="manual",
        manual_capabilities=ProviderCapabilityDeclaration(
            read_gbps=read_gbps,
            write_gbps=4,
            ops_per_second=200,
            conditional_put=conditional_put,
            encryption_at_rest=True,
            authentication=True,
            authorization_scopes=True,
            lifecycle_delete=True,
            transaction_log=True,
        ),
    )


def test_provider_assessment_blockers_and_scores() -> None:
    requirements = _requirements()
    bad = assess_remote_backend_provider(
        requirements=requirements,
        provider=_provider("bad", read_gbps=1, conditional_put=False),
    )
    good = assess_remote_backend_provider(
        requirements=requirements,
        provider=_provider("good", read_gbps=8, conditional_put=True),
    )

    assert "throughput_fit" in bad.assessment.blockers
    assert "conditional_put_support" in bad.assessment.blockers
    assert good.assessment.total_score > bad.assessment.total_score
    assert good.assessment.is_live_validated is False
    assert good.model_validate_json(good.to_json()) == good
