import json
import subprocess
import sys

import pytest

from decodilo.storage.remote_backend_evidence import (
    build_remote_backend_evidence_package,
    write_remote_backend_evidence_package,
)
from decodilo.storage.remote_backend_provider_matrix import (
    ProviderCapabilityDeclaration,
    RemoteBackendProviderCandidate,
    build_provider_comparison_matrix,
    write_provider_comparison_matrix,
)
from decodilo.storage.remote_backend_requirements import (
    RemoteBackendRequirementSet,
    write_remote_backend_requirements,
)

pytestmark = pytest.mark.integration


def test_remote_review_cli_chain(tmp_path) -> None:
    requirements = RemoteBackendRequirementSet(
        scenario_id="m017-cli",
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
    requirements_path = tmp_path / "requirements.json"
    write_remote_backend_requirements(requirements_path, requirements)
    source = tmp_path / "source.json"
    source.write_text('{"ok": true}\n', encoding="utf-8")
    evidence_path = tmp_path / "evidence-package.json"
    write_remote_backend_evidence_package(
        evidence_path,
        build_remote_backend_evidence_package(evidence_paths={"source": source}),
    )
    matrix_path = tmp_path / "provider-matrix.json"
    matrix = build_provider_comparison_matrix(
        requirements=requirements,
        providers=[
            RemoteBackendProviderCandidate(
                provider_name="manual-simulated",
                backend_type="manual",
                manual_capabilities=ProviderCapabilityDeclaration(
                    read_gbps=2,
                    write_gbps=2,
                    ops_per_second=100,
                    conditional_put=True,
                ),
            )
        ],
    )
    write_provider_comparison_matrix(matrix_path, matrix)
    readiness = tmp_path / "readiness.json"
    conformance = tmp_path / "conformance.json"
    readiness.write_text("{}", encoding="utf-8")
    conformance.write_text("{}", encoding="utf-8")

    proposal = tmp_path / "remote-proposal.json"
    result = _run(
        "proposal",
        "build",
        "--requirements",
        str(requirements_path),
        "--evidence-package",
        str(evidence_path),
        "--provider-matrix",
        str(matrix_path),
        "--provider-name",
        "manual-simulated",
        "--readiness-report",
        str(readiness),
        "--conformance-report",
        str(conformance),
        "--out",
        str(proposal),
    )
    assert json.loads(result.stdout)["launch_allowed"] is False

    guard = tmp_path / "sdk-guard.json"
    _run("sdk-guard", "--project-root", ".", "--out", str(guard))
    risk = tmp_path / "risk-register.json"
    _run("risk-register", "--proposal", str(proposal), "--out", str(risk))
    rollout = tmp_path / "rollout-plan.json"
    _run("rollout-plan", "--proposal", str(proposal), "--out", str(rollout))
    decision = tmp_path / "decision-record.json"
    decision_result = _run(
        "decision-record",
        "--proposal",
        str(proposal),
        "--evidence-package",
        str(evidence_path),
        "--readiness-report",
        str(readiness),
        "--risk-register",
        str(risk),
        "--sdk-guard-report",
        str(guard),
        "--rollout-plan",
        str(rollout),
        "--out",
        str(decision),
    )
    assert json.loads(decision_result.stdout)["status"] == "blocked_by_risk"
    review = tmp_path / "review-package.json"
    review_result = _run(
        "review-package",
        "--proposal",
        str(proposal),
        "--decision-record",
        str(decision),
        "--risk-register",
        str(risk),
        "--rollout-plan",
        str(rollout),
        "--sdk-guard-report",
        str(guard),
        "--out",
        str(review),
    )
    assert json.loads(review_result.stdout)["remote_backend_enabled"] is False


def _run(*args: str):
    return subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "remote", *args],
        check=True,
        capture_output=True,
        text=True,
    )
