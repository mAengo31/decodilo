import pytest

from decodilo.storage.remote_backend_conformance import (
    passing_simulator_config,
    run_remote_backend_conformance_suite,
)
from decodilo.storage.remote_backend_readiness import (
    RemoteBackendReadinessReport,
    RemoteBackendReadinessStatus,
    evaluate_remote_backend_readiness,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_security import evaluate_remote_backend_security


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m016-readiness",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=10,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_missing_scaling_report_is_evidence_missing() -> None:
    requirements = _requirements()
    conformance = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )
    security = evaluate_remote_backend_security(requirements=requirements)

    report = evaluate_remote_backend_readiness(
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref=None,
        requirement_ref="requirements.json",
        validation_report_ref="validation.json",
        conformance_report_ref="conformance.json",
        conformance_report=conformance,
        security_report=security,
        evidence_package=None,
    )

    assert report.readiness_status == RemoteBackendReadinessStatus.evidence_missing
    assert "learner_scaling_report_exists" in report.blockers
    assert report.remote_backend_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_simulator_conformance_pass_cannot_enable_backend() -> None:
    requirements = _requirements()
    conformance = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )
    security = evaluate_remote_backend_security(requirements=requirements)

    report = evaluate_remote_backend_readiness(
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref="scaling.json",
        requirement_ref="requirements.json",
        validation_report_ref="validation.json",
        conformance_report_ref="conformance.json",
        conformance_report=conformance,
        security_report=security,
        evidence_package=None,
    )

    assert report.readiness_status == RemoteBackendReadinessStatus.implementation_review_required
    assert "passing simulator conformance does not permit SDK addition" in report.warnings
    assert report.remote_backend_enabled is False
    assert report.launch_allowed is False


def test_missing_security_checklist_is_blocker() -> None:
    requirements = _requirements()
    conformance = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )

    report = evaluate_remote_backend_readiness(
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref="scaling.json",
        requirement_ref="requirements.json",
        validation_report_ref="validation.json",
        conformance_report_ref="conformance.json",
        conformance_report=conformance,
        security_report=None,
        evidence_package=None,
    )

    assert "security_checklist_completed" in report.blockers
    assert report.readiness_status == RemoteBackendReadinessStatus.evidence_missing


def test_raw_secret_and_sdk_dependency_are_blockers() -> None:
    requirements = _requirements()
    conformance = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )
    security = evaluate_remote_backend_security(requirements=requirements)

    report = evaluate_remote_backend_readiness(
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref="scaling.json",
        requirement_ref="requirements.json",
        validation_report_ref="validation.json",
        conformance_report_ref="conformance.json",
        conformance_report=conformance,
        security_report=security,
        evidence_package=None,
        raw_secret_detected=True,
        sdk_dependency_detected=True,
    )

    assert "no_raw_secrets_present" in report.blockers
    assert "no_real_sdk_dependency_added" in report.blockers


def test_m016_forbids_future_enabled_statuses() -> None:
    with pytest.raises(ValueError, match="cannot allow SDK addition"):
        RemoteBackendReadinessReport(
            scenario_id="bad",
            criteria=[],
            passed_criteria=[],
            failed_criteria=[],
            readiness_status=RemoteBackendReadinessStatus.sdk_addition_allowed_by_policy,
        )
