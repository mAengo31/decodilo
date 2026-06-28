"""Lambda operation backends.

The dry-run backend remains review-only and non-executable. The real Lambda
operation backend is the L6 bridge from ad-hoc operator scripts toward a
backend-owned operation layer. It is still fail-closed by default and requires
``allow_billable_action=True`` before invoking the L5 runner.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    load_lambda_l5_restart_recovery_direct_tcp_evidence_package,
)
from decodilo.lambda_cloud.launch_dry_run_lockfile import (
    build_lambda_launch_dry_run_lockfile,
    write_lambda_launch_dry_run_lockfile,
)
from decodilo.lambda_cloud.no_training_policy import (
    build_lambda_no_training_policy,
    write_lambda_no_training_policy,
)
from decodilo.operation.lambda_components import (
    LambdaOperationBackendConfig,
    build_lambda_operation_plan,
    lambda_operation_result_from_l5_package,
)
from decodilo.operation.result import OperationResult
from decodilo.operation.spec import OperationSafetyEnvelope, OperationSpec


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LambdaOperationBackend:
    """Operation backend that promotes the proven L5 Lambda runner.

    The backend is launch-disabled unless explicitly configured with
    ``allow_billable_action=True``. When armed, it invokes the L5 direct-TCP
    restart/recovery runner and normalizes the resulting evidence package into
    an ``OperationResult``.
    """

    name = "lambda"

    def __init__(
        self,
        *,
        config: LambdaOperationBackendConfig | None = None,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.config = config or LambdaOperationBackendConfig()
        self.command_runner = command_runner or _default_command_runner

    def run(self, spec: OperationSpec, *, workdir: Path) -> OperationResult:
        workdir.mkdir(parents=True, exist_ok=True)
        plan = build_lambda_operation_plan(spec, config=self.config, workdir=workdir)
        preview_path = workdir / "lambda_l6_command_preview.json"
        preview_path.write_text(plan.to_json(), encoding="utf-8")
        if not self.config.allow_billable_action:
            return OperationResult(
                operation_name=spec.name,
                backend=self.name,
                status="blocked",
                inner_optimizer_semantics=spec.inner_optimizer,
                outer_optimizer_semantics=spec.outer_optimizer,
                outer_momentum=spec.outer_momentum,
                safety=OperationSafetyEnvelope(network_scope="none"),
                backend_report={
                    "blocked_reason": "LambdaOperationBackend requires allow_billable_action=True",
                    "command_preview_path": str(preview_path),
                    "command": plan.redacted_command,
                    "operation_plan": plan.to_preview_dict(),
                },
            )

        completed = self.command_runner(plan.command, cwd=Path.cwd())
        package = load_lambda_l5_restart_recovery_direct_tcp_evidence_package(
            plan.evidence_package_path
        )
        return lambda_operation_result_from_l5_package(
            spec=spec,
            package=package,
            plan=plan,
            completed=completed,
        )


class LambdaDryRunOperationBackend:
    """Review-only Lambda backend for operation specs.

    The backend intentionally returns ``status='blocked'`` because a Lambda
    operation is not launch-ready from this code path. The generated artifacts
    document what would need review before a real backend could exist.
    """

    name = "lambda_dry_run"

    def run(self, spec: OperationSpec, *, workdir: Path) -> OperationResult:
        workdir.mkdir(parents=True, exist_ok=True)
        safety = OperationSafetyEnvelope(network_scope="none")
        spec_path = workdir / "lambda_operation_spec.json"
        no_training_path = workdir / "lambda_no_training_policy.json"
        lockfile_path = workdir / "lambda_launch_dry_run_lockfile.json"

        spec_json = spec.model_copy(update={"safety": safety}).to_json()
        spec_path.write_text(spec_json, encoding="utf-8")
        operation_spec_hash = _sha256_text(spec_json)

        no_training = build_lambda_no_training_policy()
        write_lambda_no_training_policy(no_training_path, no_training)

        launch_plan = {
            "backend": self.name,
            "operation_name": spec.name,
            "inner_optimizer": spec.inner_optimizer,
            "outer_optimizer": spec.outer_optimizer,
            "trainer_type": spec.trainer_type,
            "review_only": True,
            "executable": False,
            "blocked_reason": "Lambda backend is launch-disabled in the operation layer",
        }
        launch_plan_hash = _sha256_text(json.dumps(launch_plan, sort_keys=True))
        teardown_plan_hash = _sha256_text("review-only-no-resources-to-teardown")
        budget_lock_hash = _sha256_text("billable-action-disabled")
        approval_hash = _sha256_text("human-approval-not-requested")
        termination_runbook_hash = _sha256_text("no-process-launched")
        launch_window_policy_hash = _sha256_text("launch-window-not-open")

        lockfile = build_lambda_launch_dry_run_lockfile(
            run_id=f"{spec.name}:lambda-dry-run",
            launch_plan_hash=launch_plan_hash,
            teardown_plan_hash=teardown_plan_hash,
            budget_lock_hash=budget_lock_hash,
            approval_hash=approval_hash,
            operation_spec_hash=operation_spec_hash,
            termination_runbook_hash=termination_runbook_hash,
            launch_window_policy_hash=launch_window_policy_hash,
        )
        write_lambda_launch_dry_run_lockfile(lockfile_path, lockfile)

        return OperationResult(
            operation_name=spec.name,
            backend=self.name,
            status="blocked",
            inner_optimizer_semantics=spec.inner_optimizer,
            outer_optimizer_semantics=spec.outer_optimizer,
            outer_momentum=spec.outer_momentum,
            learners=spec.learners,
            safety=safety,
            backend_report={
                "operation_spec_path": str(spec_path),
                "operation_spec_hash": operation_spec_hash,
                "no_training_policy_path": str(no_training_path),
                "launch_dry_run_lockfile_path": str(lockfile_path),
                "launch_dry_run_lockfile": lockfile.model_dump(mode="json"),
                "training_allowed": no_training.training_allowed,
                "dataset_download_allowed": no_training.dataset_download_allowed,
                "model_download_allowed": no_training.model_download_allowed,
                "gpu_benchmark_allowed": no_training.gpu_benchmark_allowed,
                "blocked_reason": launch_plan["blocked_reason"],
            },
        )


def _default_command_runner(
    command: list[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=1800,
        check=False,
    )
