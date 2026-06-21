import pytest

from decodilo.storage.remote_backend_proposal import RemoteBackendImplementationProposal
from decodilo.storage.remote_backend_sdk_guard import scan_json_for_secret_like_values


def test_review_artifact_secret_scan_detects_raw_secret_field() -> None:
    findings = scan_json_for_secret_like_values({"auth": {"password": "redacted"}})

    assert "$.auth.password" in findings


def test_proposal_rejects_secret_like_values() -> None:
    with pytest.raises(ValueError, match="secret-like"):
        RemoteBackendImplementationProposal(
            proposal_id="bad",
            provider_candidate_name="AKIA1234567890123456",
            backend_type="manual",
            source_readiness_report_ref="readiness.json",
            source_evidence_package_ref="evidence.json",
            source_conformance_report_ref="conformance.json",
            source_requirement_ref="requirements.json",
            target_learner_count=1,
            stress_learner_count=1,
            target_read_gbps=1,
            target_write_gbps=1,
            target_ops_per_second=1,
            target_checkpoint_growth_gb_per_hour=1,
            target_replay_snapshot_frequency="every checkpoint",
            dependency_plan={},
        )
