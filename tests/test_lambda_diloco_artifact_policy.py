from __future__ import annotations

import json

from lambda_m081s_helpers import write_m081r_manifest

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.diloco_artifact_policy import (
    build_lambda_diloco_artifact_policy_report_from_path,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_lambda_remote_vslice_manifest_artifact_policy_from_path,
    write_lambda_remote_vslice_manifest_artifact_policy,
)


def test_diloco_artifact_policy_passes_for_manifest_declared_diloco_path(tmp_path):
    policy_path = tmp_path / "manifest-artifact-policy.json"
    write_lambda_remote_vslice_manifest_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_manifest_artifact_policy_from_path(
            manifest=write_m081r_manifest(tmp_path / "manifest.json"),
        ),
    )

    report = build_lambda_diloco_artifact_policy_report_from_path(
        manifest_artifact_policy=policy_path,
    )

    assert report.policy_status == "policy_passed"
    assert report.diloco_declared_artifact_supported is True
    assert report.manifest_driven is True
    assert report.no_arbitrary_file_reads is True
    assert report.reject_undeclared_paths is True
    assert report.reject_symlink_escapes is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_manifest_artifact_policy_reads_redacted_tokens_from_exact_command(tmp_path):
    command = (
        "env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src python3 "
        "-m decodilo.cli dev diloco-smoke --synthetic --learners 1 "
        "--sync-rounds 1 --max-steps 1 --out "
        f"{DILOCO_SMOKE_DECLARED_ARTIFACT_PATH}"
    )
    manifest = tmp_path / "redacted-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "milestone": "M081R",
                "command_entries": [
                    {
                        "stage": "diloco_smoke_command",
                        "argv_tokens": "<redacted>",
                        "exact_command": command,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    policy = build_lambda_remote_vslice_manifest_artifact_policy_from_path(
        manifest=manifest,
    )

    assert policy.policy_status == "manifest_artifact_policy_defined"
    assert policy.declared_artifact_path == DILOCO_SMOKE_DECLARED_ARTIFACT_PATH
    assert policy.diloco_smoke_declared_artifact_supported is True
