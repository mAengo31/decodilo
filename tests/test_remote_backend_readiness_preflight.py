import json
import subprocess
import sys
from pathlib import Path

import pytest

from decodilo.cloud.remote_backend_readiness_preflight import (
    collect_remote_backend_readiness_preflight,
)
from decodilo.storage.remote_backend_conformance import (
    passing_simulator_config,
    run_remote_backend_conformance_suite,
    write_remote_backend_conformance_report,
)
from decodilo.storage.remote_backend_provider_matrix import (
    ProviderCapabilityDeclaration,
    RemoteBackendProviderCandidate,
    build_provider_comparison_matrix,
    write_provider_comparison_matrix,
)
from decodilo.storage.remote_backend_readiness import (
    evaluate_remote_backend_readiness,
    write_remote_backend_readiness_report,
)
from decodilo.storage.remote_backend_requirements import (
    RemoteBackendRequirementSet,
    write_remote_backend_requirements,
)
from decodilo.storage.remote_backend_security import (
    evaluate_remote_backend_security,
    write_remote_backend_security_report,
)

pytestmark = pytest.mark.integration


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m016-preflight",
        target_learner_count=2,
        stress_learner_count=4,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=10,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_readiness_preflight_reports_missing_evidence(tmp_path: Path) -> None:
    evidence = collect_remote_backend_readiness_preflight(root=tmp_path)

    assert evidence["summary"]["remote_backend_enabled"] is False
    assert "remote backend readiness report missing" in evidence["warnings"]
    assert "remote backend conformance report missing" in evidence["warnings"]
    assert "remote backend evidence package missing" in evidence["warnings"]


def test_readiness_preflight_includes_present_evidence(tmp_path: Path) -> None:
    requirements = _requirements()
    conformance = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )
    security = evaluate_remote_backend_security(requirements=requirements)
    readiness = evaluate_remote_backend_readiness(
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref="scaling.json",
        requirement_ref="remote_backend_requirements.json",
        validation_report_ref="remote_backend_design_validation.json",
        conformance_report_ref="remote_conformance.json",
        conformance_report=conformance,
        security_report=security,
        evidence_package=None,
    )
    write_remote_backend_conformance_report(tmp_path / "remote_conformance.json", conformance)
    write_remote_backend_readiness_report(tmp_path / "remote_backend_readiness.json", readiness)
    write_remote_backend_security_report(tmp_path / "remote-security.json", security)
    matrix = build_provider_comparison_matrix(
        requirements=requirements,
        providers=[
            RemoteBackendProviderCandidate(
                provider_name="manual",
                backend_type="manual",
                manual_capabilities=ProviderCapabilityDeclaration(
                    read_gbps=2,
                    write_gbps=2,
                    ops_per_second=20,
                ),
            )
        ],
    )
    write_provider_comparison_matrix(tmp_path / "provider_matrix.json", matrix)

    evidence = collect_remote_backend_readiness_preflight(root=tmp_path)

    assert evidence["summary"]["readiness_status"] == "implementation_review_required"
    assert evidence["summary"]["conformance_passed"] is True
    assert evidence["summary"]["provider_count"] == 1
    assert "simulator conformance is not production backend readiness" in evidence["warnings"]


def test_remote_cli_conformance_readiness_and_evidence(tmp_path: Path) -> None:
    requirements = _requirements()
    requirements_path = tmp_path / "remote_backend_requirements.json"
    sim_config_path = tmp_path / "simulator-config.json"
    conformance_path = tmp_path / "remote_conformance.json"
    security_path = tmp_path / "remote-security.json"
    validation_path = tmp_path / "remote_backend_design_validation.json"
    readiness_path = tmp_path / "remote_backend_readiness.json"
    evidence_path = tmp_path / "remote_backend_evidence_package.json"
    scaling_path = tmp_path / "scaling.json"
    cost_path = tmp_path / "cost.json"
    write_remote_backend_requirements(requirements_path, requirements)
    sim_config_path.write_text(
        passing_simulator_config(requirements).model_dump_json(),
        encoding="utf-8",
    )
    security = evaluate_remote_backend_security(requirements=requirements)
    write_remote_backend_security_report(security_path, security)
    validation_path.write_text(
        '{"recommendation":{"design_status":"not_ready"}}\n',
        encoding="utf-8",
    )
    scaling_path.write_text('{"kind":"scaling"}\n', encoding="utf-8")
    cost_path.write_text('{"kind":"cost"}\n', encoding="utf-8")

    conformance_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "conformance",
            "run",
            "--requirements",
            str(requirements_path),
            "--simulator-config",
            str(sim_config_path),
            "--out",
            str(conformance_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(conformance_run.stdout)["passed"] is True

    readiness_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "readiness",
            "evaluate",
            "--requirements",
            str(requirements_path),
            "--validation-report",
            str(validation_path),
            "--conformance-report",
            str(conformance_path),
            "--security-report",
            str(security_path),
            "--scaling-report",
            str(scaling_path),
            "--out",
            str(readiness_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(readiness_run.stdout)["launch_allowed"] is False

    evidence_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "evidence",
            "build",
            "--workdir",
            str(tmp_path),
            "--scaling-report",
            str(scaling_path),
            "--requirements",
            str(requirements_path),
            "--validation-report",
            str(validation_path),
            "--conformance-report",
            str(conformance_path),
            "--security-report",
            str(security_path),
            "--cost-report",
            str(cost_path),
            "--readiness-report",
            str(readiness_path),
            "--out",
            str(evidence_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(evidence_run.stdout)["evidence_completeness_score"] == 1.0
