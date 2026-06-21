import json
import subprocess
import sys

import pytest

from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.learner_scaling_model import evaluate_learner_scaling
from decodilo.scaling.scaling_report import write_scaling_decision_report

pytestmark = pytest.mark.integration


def test_remote_backend_cli_commands(tmp_path) -> None:
    scenario = LearnerPodScalingScenario(
        scenario_id="remote-cli",
        mode="fixed_total_compute",
        candidate_learner_counts=[1, 2],
        fixed_total_gpus=4,
        training_duration_hours=1,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
        calibration_profile={
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0.01,
            "recovery_time_seconds": 300,
        },
    )
    scaling_path = tmp_path / "scaling.json"
    write_scaling_decision_report(scaling_path, evaluate_learner_scaling(scenario))
    requirements_path = tmp_path / "remote_backend_requirements.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "requirements",
            "--scaling-report",
            str(scaling_path),
            "--out",
            str(requirements_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(requirements_path.read_text(encoding="utf-8"))[
        "target_learner_count"
    ] > 0

    sim_path = tmp_path / "remote-sim.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "simulate-backend",
            "--requirements",
            str(requirements_path),
            "--read-gbps",
            "10",
            "--write-gbps",
            "5",
            "--ops-per-second",
            "1000",
            "--strong-consistency",
            "--conditional-put",
            "--object-versioning",
            "--out",
            str(sim_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    design_path = tmp_path / "remote_backend_design_validation.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "validate-design",
            "--requirements",
            str(requirements_path),
            "--sim-report",
            str(sim_path),
            "--out",
            str(design_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    design = json.loads(design_path.read_text(encoding="utf-8"))
    assert design["recommendation"]["remote_backend_enabled"] is False
    assert design["recommendation"]["launch_allowed"] is False

    security_path = tmp_path / "security.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "security-check",
            "--requirements",
            str(requirements_path),
            "--out",
            str(security_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(security_path.read_text(encoding="utf-8"))["passed"] is True

    cost_profile = tmp_path / "cost-profile.json"
    cost_profile.write_text(
        json.dumps(
            {
                "storage_cost_per_gb_hour": 0.01,
                "read_cost_per_1000_ops": 0.001,
                "write_cost_per_1000_ops": 0.001,
                "list_cost_per_1000_ops": 0.001,
                "delete_cost_per_1000_ops": 0.001,
                "egress_cost_per_gb": 0.01,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    cost_path = tmp_path / "cost.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "remote",
            "cost-estimate",
            "--requirements",
            str(requirements_path),
            "--cost-profile-json",
            str(cost_profile),
            "--out",
            str(cost_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(cost_path.read_text(encoding="utf-8"))[
        "total_backend_cost_per_hour"
    ] >= 0
