from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    LambdaM073RTinySmokeAuthorization,
    write_lambda_m073r_tiny_smoke_authorization,
)


def make_m073r_upload_failure_workdir(
    tmp_path: Path,
    *,
    stderr: str = (
        "Connection timed out during banner exchange\n"
        "Connection to <redacted-host> port 22 timed out\n"
        "scp: Connection closed"
    ),
    final_instance_count: int = 0,
    final_unmanaged_count: int = 0,
) -> tuple[Path, Path]:
    workdir = tmp_path / "m073r"
    workdir.mkdir()
    report = {
        "run_id": "lambda-m073r-tiny-smoke",
        "failed_stage": "source_bundle_upload",
        "source_bundle_upload_attempted": True,
        "source_bundle_upload_succeeded": False,
        "source_bundle_hash_verified": False,
        "dependency_bundle_upload_attempted": False,
        "dependency_bundle_hash_verified": False,
        "remote_command_stage_results": [],
        "vertical_slice_status": "source_bundle_upload_failed",
        "training_attempted": False,
        "termination_verified": True,
        "billable_action_performed": True,
        "launch_ready": False,
        "launch_allowed": False,
        "errors": ["source_bundle_upload_failed"],
    }
    evidence = {
        "stderr_redacted": stderr,
        "stderr_secret_scan_passed": True,
        "failed_stage": "source_bundle_upload",
        "source_bundle_upload_attempted": True,
        "source_bundle_upload_succeeded": False,
        "dependency_bundle_upload_attempted": False,
        "vertical_slice_status": "source_bundle_upload_failed",
        "training_attempted": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    post = {
        "instance_count": final_instance_count,
        "unmanaged_count": final_unmanaged_count,
        "launch_ready": False,
        "launch_allowed": False,
    }
    (workdir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (workdir / "remote-vslice-evidence.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )
    post_path = tmp_path / "post-summary.json"
    post_path.write_text(json.dumps(post), encoding="utf-8")
    (workdir / "post-discovery-summary-final.json").write_text(
        json.dumps(post),
        encoding="utf-8",
    )
    return workdir, post_path


def make_future_tiny_smoke_authorization(path: Path) -> Path:
    write_lambda_m073r_tiny_smoke_authorization(
        path,
        LambdaM073RTinySmokeAuthorization(
            authorization_status="authorized_for_future_m073r_tiny_decodilo_smoke",
        ),
    )
    return path
