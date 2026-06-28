"""Phase 3: launch-disabled Lambda mapping for the operation layer.

This is deliberately offline and non-executable. It proves the pathway/op layer
can map a tiny AdamW/Nesterov operation toward Lambda review artifacts while
still forbidding launch, training, downloads, remote backend enablement, and
billable actions.
"""

from __future__ import annotations

import json

import pytest

from decodilo.lambda_cloud.launch_dry_run_lockfile import load_lambda_launch_dry_run_lockfile
from decodilo.lambda_cloud.no_training_policy import load_lambda_no_training_policy
from decodilo.operation import LambdaDryRunOperationBackend, OperationSpec, run_operation

pytestmark = [pytest.mark.lambda_offline, pytest.mark.cloud_disabled]


def test_lambda_dry_run_backend_generates_disabled_review_artifacts(tmp_path) -> None:
    spec = OperationSpec(name="tiny-adamw-nesterov-lambda-review")
    result = run_operation(spec, workdir=tmp_path, backend=LambdaDryRunOperationBackend())

    assert result.backend == "lambda_dry_run"
    assert result.status == "blocked"
    assert result.inner_optimizer_semantics == "adamw"
    assert result.outer_optimizer_semantics == "nesterov"

    assert result.safety.network_scope == "none"
    assert result.safety.launch_ready is False
    assert result.safety.launch_allowed is False
    assert result.safety.billable_action_performed is False
    assert result.safety.remote_backend_enabled is False

    spec_path = tmp_path / "lambda_operation_spec.json"
    no_training_path = tmp_path / "lambda_no_training_policy.json"
    lockfile_path = tmp_path / "lambda_launch_dry_run_lockfile.json"
    assert spec_path.exists()
    assert no_training_path.exists()
    assert lockfile_path.exists()

    rendered_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert rendered_spec["inner_optimizer"] == "adamw"
    assert rendered_spec["outer_optimizer"] == "nesterov"
    assert rendered_spec["safety"]["network_scope"] == "none"
    assert rendered_spec["safety"]["launch_allowed"] is False

    no_training = load_lambda_no_training_policy(no_training_path)
    assert no_training.training_allowed is False
    assert no_training.dataset_download_allowed is False
    assert no_training.model_download_allowed is False
    assert no_training.gpu_benchmark_allowed is False
    assert no_training.launch_allowed is False
    assert no_training.billable_action_performed is False

    lockfile = load_lambda_launch_dry_run_lockfile(lockfile_path)
    assert lockfile.locked_for_review_only is True
    assert lockfile.executable is False
    assert lockfile.launch_ready is False
    assert lockfile.launch_allowed is False
    assert lockfile.real_mutation_enabled is False
    assert lockfile.billable_action_performed is False
    assert lockfile.operation_spec_hash == result.backend_report["operation_spec_hash"]


def test_lambda_dry_run_backend_does_not_report_runtime_success(tmp_path) -> None:
    result = run_operation(
        OperationSpec(name="blocked-lambda-review"),
        workdir=tmp_path,
        backend=LambdaDryRunOperationBackend(),
    )

    assert result.status == "blocked"
    assert result.final_global_version == 0
    assert result.sync_rounds_committed == 0
    assert result.training_attempted is False
    assert result.real_training_mechanics_exercised is False
    assert result.replay_passed is False
    assert result.metric_validation_passed is False
    assert "blocked_reason" in result.backend_report
