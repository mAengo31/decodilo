from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

from test_lambda_m061_whoami_identity_command import _write_m061_inputs

from decodilo.lambda_cloud import remote_vertical_slice_policy
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.remote_dependency_bundle import (
    LambdaDependencyBundleManifest,
    build_lambda_dependency_bundle_from_paths,
    build_lambda_m067r_dependency_failure_record_from_paths,
    build_lambda_m068r_dependency_bundle_default_manifest,
    build_lambda_runtime_dependency_inventory_from_paths,
    validate_lambda_dependency_bundle_from_paths,
    write_lambda_dependency_bundle_manifest,
    write_lambda_dependency_bundle_validation,
    write_lambda_m067r_dependency_failure_record,
    write_lambda_runtime_dependency_inventory,
)
from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M067R_REMOTE_BUNDLE_PATH,
    M067R_REMOTE_EXTRACT_DIR,
    M067R_REMOTE_IMPORT_PROBE_PATH,
    M068R_MILESTONE,
    M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
    M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
    M068R_REMOTE_RUNTIME_TARGET_DIR,
    M071R_FIRST_EXPERIMENT_COMMAND,
    M071R_MANIFEST_COMMAND_LABEL,
    M071R_MILESTONE,
    M073R_MANIFEST_COMMAND_LABEL,
    M073R_MILESTONE,
    M073R_REMOTE_BUNDLE_PATH,
    M073R_TINY_SMOKE_COMMAND,
    M077R_MANIFEST_COMMAND_LABEL,
    M077R_MILESTONE,
    M077R_REMOTE_BUNDLE_PATH,
    M077R_SYNTHETIC_EXPERIMENT_COMMAND,
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    _real_m066r_ssh_command,
    build_lambda_remote_dependency_bundle_execution_plan_from_paths,
    build_lambda_remote_dependency_bundle_gate_check_from_paths,
    build_lambda_remote_dependency_bundle_one_shot_arming_from_paths,
    build_lambda_remote_source_bundle,
    build_lambda_remote_source_bundle_default_manifest,
    build_lambda_remote_source_bundle_execution_plan_from_paths,
    build_lambda_remote_source_bundle_gate_check_from_paths,
    build_lambda_remote_source_bundle_one_shot_arming_from_paths,
    build_lambda_remote_vertical_slice_default_manifest,
    build_lambda_remote_vertical_slice_execution_plan_from_paths,
    build_lambda_remote_vertical_slice_gate_check_from_paths,
    build_lambda_remote_vertical_slice_one_shot_arming_from_paths,
    build_lambda_remote_vertical_slice_policy,
    build_lambda_remote_vertical_slice_reviewer_bridge_from_path,
    render_lambda_remote_vertical_slice_argv,
    run_lambda_remote_vertical_slice_manifest,
    validate_lambda_remote_source_bundle_from_paths,
    validate_lambda_remote_vertical_slice_manifest_from_paths,
    write_lambda_remote_source_bundle_validation,
    write_lambda_remote_vertical_slice_command_manifest,
    write_lambda_remote_vertical_slice_execution_plan,
    write_lambda_remote_vertical_slice_gate_check,
    write_lambda_remote_vertical_slice_manifest_validation,
    write_lambda_remote_vertical_slice_one_shot_arming,
    write_lambda_remote_vertical_slice_policy,
    write_lambda_remote_vertical_slice_reviewer_bridge,
)
from decodilo.lambda_cloud.ssh_host_discovery import LambdaSSHHostDiscoveryResult


def _write_m066r_inputs(tmp_path: Path) -> dict[str, Path]:
    base = _write_m061_inputs(tmp_path / "base")
    paths = {
        **base,
        "m066r_policy": tmp_path / "m066r-policy.json",
        "m066r_manifest": tmp_path / "m066r-manifest.json",
        "m066r_manifest_validation": tmp_path / "m066r-manifest-validation.json",
        "m066r_plan": tmp_path / "m066r-plan.json",
        "m066r_gate": tmp_path / "m066r-gate.json",
        "m066r_arming": tmp_path / "m066r-arming.json",
        "m066r_bridge": tmp_path / "m066r-bridge.json",
    }
    write_lambda_remote_vertical_slice_policy(
        paths["m066r_policy"],
        build_lambda_remote_vertical_slice_policy(),
    )
    write_lambda_remote_vertical_slice_command_manifest(
        paths["m066r_manifest"],
        build_lambda_remote_vertical_slice_default_manifest(),
    )
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m066r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m066r_manifest"],
            policy=paths["m066r_policy"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m066r_plan"],
        build_lambda_remote_vertical_slice_execution_plan_from_paths(
            discovery_report=base["live_discovery"],
            manifest=paths["m066r_manifest"],
            manifest_validation=paths["m066r_manifest_validation"],
            ssh_key_selection=base["ssh_selection"],
            price_snapshot=base["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m066r_gate"],
        build_lambda_remote_vertical_slice_gate_check_from_paths(
            plan=paths["m066r_plan"],
            policy=paths["m066r_policy"],
            manifest_validation=paths["m066r_manifest_validation"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m066r_arming"],
        build_lambda_remote_vertical_slice_one_shot_arming_from_paths(
            gate_check=paths["m066r_gate"],
            manifest=paths["m066r_manifest"],
            response_loss_controls=base["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m066r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m066r_arming"],
        ),
    )
    return paths


def _minimal_source_project(tmp_path: Path) -> Path:
    root = tmp_path / "source-project"
    package = root / "src" / "decodilo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("__version__ = '0.test'\n", encoding="utf-8")
    (package / "cli.py").write_text(
        "def main():\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'decodilo-test-bundle'\nversion = '0.test'\n",
        encoding="utf-8",
    )
    probe_dir = root / "tools" / "remote_probe"
    probe_dir.mkdir(parents=True)
    (probe_dir / "import_decodilo.py").write_text(
        "from __future__ import annotations\n\n"
        "import decodilo\n\n"
        "_ = decodilo\n\n"
        "print('decodilo import ok')\n",
        encoding="utf-8",
    )
    return root


def _write_m067r_inputs(tmp_path: Path) -> dict[str, Path]:
    base = _write_m061_inputs(tmp_path / "base")
    source_root = _minimal_source_project(tmp_path)
    paths = {
        **base,
        "m067r_policy": tmp_path / "m067r-policy.json",
        "m067r_bundle": tmp_path / "decodilo-source-bundle-m067r.tar.gz",
        "m067r_bundle_manifest": tmp_path / "m067r-bundle-manifest.json",
        "m067r_bundle_validation": tmp_path / "m067r-bundle-validation.json",
        "m067r_manifest": tmp_path / "m067r-manifest.json",
        "m067r_manifest_validation": tmp_path / "m067r-manifest-validation.json",
        "m067r_plan": tmp_path / "m067r-plan.json",
        "m067r_gate": tmp_path / "m067r-gate.json",
        "m067r_arming": tmp_path / "m067r-arming.json",
        "m067r_bridge": tmp_path / "m067r-bridge.json",
    }
    write_lambda_remote_vertical_slice_policy(
        paths["m067r_policy"],
        build_lambda_remote_vertical_slice_policy(),
    )
    build_lambda_remote_source_bundle(
        project_root=source_root,
        bundle=paths["m067r_bundle"],
        manifest_out=paths["m067r_bundle_manifest"],
    )
    write_lambda_remote_source_bundle_validation(
        paths["m067r_bundle_validation"],
        validate_lambda_remote_source_bundle_from_paths(
            bundle=paths["m067r_bundle"],
            manifest=paths["m067r_bundle_manifest"],
        ),
    )
    write_lambda_remote_vertical_slice_command_manifest(
        paths["m067r_manifest"],
        build_lambda_remote_source_bundle_default_manifest(),
    )
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m067r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m067r_manifest"],
            policy=paths["m067r_policy"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m067r_plan"],
        build_lambda_remote_source_bundle_execution_plan_from_paths(
            discovery_report=base["live_discovery"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            command_manifest=paths["m067r_manifest"],
            manifest_validation=paths["m067r_manifest_validation"],
            ssh_key_selection=base["ssh_selection"],
            price_snapshot=base["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m067r_gate"],
        build_lambda_remote_source_bundle_gate_check_from_paths(
            plan=paths["m067r_plan"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m067r_arming"],
        build_lambda_remote_source_bundle_one_shot_arming_from_paths(
            gate_check=paths["m067r_gate"],
            command_manifest=paths["m067r_manifest"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            response_loss_controls=base["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m067r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m067r_arming"],
        ),
    )
    return paths


def _write_m068r_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = _write_m067r_inputs(tmp_path)
    paths.update(
        {
            "m068r_dep_bundle": tmp_path / "decodilo-dependency-bundle-m068w.tar.gz",
            "m068r_dep_manifest": tmp_path / "m068r-dependency-bundle.manifest.json",
            "m068r_dep_validation": tmp_path / "m068r-dependency-validation.json",
        }
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    for name in (
        "pydantic-2.0.0-py3-none-any.whl",
        "pydantic_core-2.0.0-cp310-cp310-manylinux2014_x86_64.whl",
    ):
        (wheelhouse / name).write_text("fake wheel\n", encoding="utf-8")
    with tarfile.open(paths["m068r_dep_bundle"], "w:gz") as tar:
        for wheel in sorted(wheelhouse.iterdir()):
            tar.add(wheel, arcname=wheel.name)
    dep_sha = _sha256(paths["m068r_dep_bundle"])
    write_lambda_dependency_bundle_manifest(
        paths["m068r_dep_manifest"],
        LambdaDependencyBundleManifest(
            bundle_status="bundle_created",
            bundle_path=str(paths["m068r_dep_bundle"]),
            dependency_items=["pydantic", "pydantic-core"],
            versions={"pydantic": "2.0.0", "pydantic-core": "2.0.0"},
            source="local_wheelhouse",
            total_bytes=paths["m068r_dep_bundle"].stat().st_size,
            sha256=dep_sha,
            secret_scan_passed=True,
            platform_compatibility_notes=["manylinux cp310 fixture"],
            internet_download_used=True,
        ),
    )
    write_lambda_dependency_bundle_validation(
        paths["m068r_dep_validation"],
        validate_lambda_dependency_bundle_from_paths(
            bundle=paths["m068r_dep_bundle"],
            manifest=paths["m068r_dep_manifest"],
            inventory=_write_m068r_inventory_fixture(tmp_path),
        ),
    )
    write_lambda_remote_vertical_slice_command_manifest(
        paths["m067r_manifest"],
        build_lambda_m068r_dependency_bundle_default_manifest(),
    )
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m067r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m067r_manifest"],
            policy=paths["m067r_policy"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m067r_plan"],
        build_lambda_remote_dependency_bundle_execution_plan_from_paths(
            discovery_report=paths["live_discovery"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            command_manifest=paths["m067r_manifest"],
            manifest_validation=paths["m067r_manifest_validation"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m067r_gate"],
        build_lambda_remote_dependency_bundle_gate_check_from_paths(
            plan=paths["m067r_plan"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m067r_arming"],
        build_lambda_remote_dependency_bundle_one_shot_arming_from_paths(
            gate_check=paths["m067r_gate"],
            command_manifest=paths["m067r_manifest"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m067r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m067r_arming"],
        ),
    )
    return paths


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_m068r_inventory_fixture(tmp_path: Path) -> Path:
    inventory_path = tmp_path / "m068r-runtime-dependency-inventory.json"
    write_lambda_runtime_dependency_inventory(
        inventory_path,
        build_lambda_runtime_dependency_inventory_from_paths(
            pyproject=Path("pyproject.toml"),
            failure_record=_m068r_failure_fixture(tmp_path),
        ),
    )
    return inventory_path


def test_m066r_manifest_validation_blocks_forbidden_package_install(tmp_path):
    policy = tmp_path / "policy.json"
    manifest = tmp_path / "manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    write_lambda_remote_vertical_slice_command_manifest(
        manifest,
        LambdaRemoteVerticalSliceCommandManifest(
            max_remote_commands=1,
            command_entries=[
                LambdaRemoteVerticalSliceCommandEntry(
                    stage="forbidden_install",
                    exact_command="pip install decodilo",
                    argv_tokens=["pip", "install", "decodilo"],
                    failure_stage_if_nonzero="forbidden_install",
                )
            ],
        ),
    )

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest,
        policy=policy,
    )

    assert validation.validation_passed is False
    assert any("package_install" in blocker for blocker in validation.blockers)
    assert validation.launch_ready is False
    assert validation.launch_allowed is False


def test_m067r3_default_manifest_uses_probe_script_not_inline_python(tmp_path):
    manifest = build_lambda_remote_source_bundle_default_manifest()

    hash_entry = next(
        entry
        for entry in manifest.command_entries
        if entry.stage == "source_bundle_hash_check"
    )
    import_entry = next(
        entry
        for entry in manifest.command_entries
        if entry.stage == "decodilo_import_check"
    )

    assert hash_entry.argv_tokens == ["sha256sum", M067R_REMOTE_BUNDLE_PATH]
    assert "-c" not in import_entry.argv_tokens
    assert import_entry.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-src/src",
        "python3",
        M067R_REMOTE_IMPORT_PROBE_PATH,
    ]
    assert import_entry.exact_command == render_lambda_remote_vertical_slice_argv(
        import_entry.argv_tokens
    )
    assert shlex.split(import_entry.exact_command) == import_entry.argv_tokens


def test_m067r3_manifest_validation_rejects_previous_broken_inline_command(tmp_path):
    policy = tmp_path / "policy.json"
    manifest = tmp_path / "manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "milestone": "M067R",
                "stop_on_first_failure": True,
                "max_remote_commands": 1,
                "command_entries": [
                    {
                        "stage": "decodilo_import_check",
                        "exact_command": (
                            "env PYTHONPATH=/tmp/decodilo-src/src python3 -c "
                            "import decodilo; print('decodilo import ok')"
                        ),
                        "argv_tokens": [
                            "env",
                            "PYTHONPATH=/tmp/decodilo-src/src",
                            "python3",
                            "-c",
                            "import decodilo; print('decodilo import ok')",
                        ],
                        "failure_stage_if_nonzero": "decodilo_import_check",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest,
        policy=policy,
    )

    assert validation.validation_passed is False
    assert any("forbidden_python_inline_code" in item for item in validation.blockers)
    assert any("forbidden_shell_metacharacter" in item for item in validation.blockers)
    assert validation.launch_ready is False
    assert validation.launch_allowed is False


def test_m067r3_manifest_validation_rejects_raw_shell_string_commands(tmp_path):
    policy = tmp_path / "policy.json"
    manifest = tmp_path / "manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "milestone": "M067R",
                "stop_on_first_failure": True,
                "max_remote_commands": 1,
                "command_entries": [
                    {
                        "stage": "decodilo_import_check",
                        "command": (
                            "env PYTHONPATH=/tmp/decodilo-src/src python3 -c "
                            "'import decodilo; print(1)'"
                        ),
                        "failure_stage_if_nonzero": "decodilo_import_check",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest,
        policy=policy,
    )

    assert validation.validation_passed is False
    assert any("raw_shell_command_string" in item for item in validation.blockers)
    assert any("argv_tokens_required" in item for item in validation.blockers)


def test_m067r3_manifest_validation_rejects_shell_metacharacter_tokens(tmp_path):
    policy = tmp_path / "policy.json"
    manifest = tmp_path / "manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    entry = LambdaRemoteVerticalSliceCommandEntry(
        stage="decodilo_import_check",
        exact_command=render_lambda_remote_vertical_slice_argv(
            ["python3", "/tmp/decodilo-src/tools/remote_probe/import_decodilo.py;whoami"]
        ),
        argv_tokens=[
            "python3",
            "/tmp/decodilo-src/tools/remote_probe/import_decodilo.py;whoami",
        ],
        failure_stage_if_nonzero="decodilo_import_check",
    )
    write_lambda_remote_vertical_slice_command_manifest(
        manifest,
        LambdaRemoteVerticalSliceCommandManifest(
            milestone="M067R",
            max_remote_commands=1,
            command_entries=[entry],
        ),
    )

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest,
        policy=policy,
    )

    assert validation.validation_passed is False
    assert any("forbidden_shell_metacharacter" in item for item in validation.blockers)


def test_m067r3_safe_ssh_renderer_preserves_argv_boundaries(tmp_path):
    private_key = tmp_path / "id_ed25519"
    private_key.write_text("not-a-real-key\n", encoding="utf-8")
    argv = [
        "env",
        "PYTHONPATH=/tmp/decodilo-src/src",
        "python3",
        M067R_REMOTE_IMPORT_PROBE_PATH,
    ]

    rendered = render_lambda_remote_vertical_slice_argv(argv)
    ssh_command = _real_m066r_ssh_command(
        host="203.0.113.10",
        private_key_path=private_key,
        ssh_username="ubuntu",
        argv_tokens=argv,
        milestone="M067R",
    )

    assert shlex.split(rendered) == argv
    assert ssh_command[-1] == rendered
    assert shlex.split(ssh_command[-1]) == argv


def test_source_upload_is_blocked_until_ssh_banner_readiness(
    tmp_path,
    monkeypatch,
):
    private_key = tmp_path / "id_ed25519"
    private_key.write_text("not-a-real-key\n", encoding="utf-8")
    private_key.chmod(0o600)
    source_bundle = tmp_path / "source.tar.gz"
    source_bundle.write_bytes(b"source bundle")
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone="M067R",
        max_remote_commands=1,
        command_entries=[
            LambdaRemoteVerticalSliceCommandEntry(
                stage="python_version_check",
                exact_command="python3 --version",
                argv_tokens=["python3", "--version"],
                failure_stage_if_nonzero="python_version_check",
            )
        ],
    )
    host_discovery = LambdaSSHHostDiscoveryResult(
        status="FOUND",
        host="203.0.113.10",
        host_redacted="203.0.113.x",
        source_path="data[0].ip",
    )
    monkeypatch.setattr(
        remote_vertical_slice_policy,
        "_wait_for_ssh_port_ready",
        lambda **_kwargs: SimpleNamespace(
            reachable=True,
            poll_count=1,
            elapsed_seconds=0.01,
        ),
    )
    monkeypatch.setattr(
        remote_vertical_slice_policy,
        "_wait_for_ssh_banner_ready",
        lambda **_kwargs: remote_vertical_slice_policy._SSHBannerReadiness(
            ready=False,
            poll_count=2,
            elapsed_seconds=3.0,
            banner_prefix_observed=False,
        ),
    )

    evidence = run_lambda_remote_vertical_slice_manifest(
        owned_instance_id="instance-1234567890abcdef",
        instance_payload={},
        private_key_path=private_key,
        manifest=manifest,
        manifest_hash="manifest-hash",
        source_bundle_path=source_bundle,
        source_bundle_sha256="source-sha",
        host_discovery_result=host_discovery,
    )

    assert evidence.vertical_slice_status == "ssh_banner_not_ready"
    assert evidence.failed_stage == "ssh_banner_readiness"
    assert evidence.ssh_port_reachable is True
    assert evidence.ssh_banner_readiness_attempted is True
    assert evidence.ssh_banner_ready is False
    assert evidence.source_bundle_upload_attempted is False
    assert evidence.dependency_bundle_upload_attempted is False
    assert evidence.remote_command_attempted is False
    assert "ssh_banner_not_ready_before_upload" in evidence.blockers


def test_m066r_artifact_chain_selects_live_a10_and_stays_non_executable(tmp_path):
    paths = _write_m066r_inputs(tmp_path)

    manifest = json.loads(paths["m066r_manifest"].read_text())
    validation = json.loads(paths["m066r_manifest_validation"].read_text())
    plan = json.loads(paths["m066r_plan"].read_text())
    gate = json.loads(paths["m066r_gate"].read_text())
    bridge = json.loads(paths["m066r_bridge"].read_text())

    assert [entry["stage"] for entry in manifest["command_entries"]] == [
        "python_version_check",
        "decodilo_cli_help_check",
        "decodilo_profile_summary_check",
    ]
    assert validation["validation_passed"] is True
    assert plan["plan_status"] == "plan_passed"
    assert plan["selected_candidate"] == "gpu_1x_a10"
    assert plan["selected_region"] == "us-east-1"
    assert gate["gate_passed"] is True
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_remote_vertical_slice_permitted"] is True
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m066r_fake_server_runs_manifest_and_terminates(tmp_path):
    paths = _write_m066r_inputs(tmp_path)
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m066r-policy",
        str(paths["m066r_policy"]),
        "--m066r-command-manifest",
        str(paths["m066r_manifest"]),
        "--m066r-manifest-validation",
        str(paths["m066r_manifest_validation"]),
        "--m066r-plan",
        str(paths["m066r_plan"]),
        "--m066r-gate-check",
        str(paths["m066r_gate"]),
        "--m066r-one-shot-arming",
        str(paths["m066r_arming"]),
        "--m066r-reviewer-bridge",
        str(paths["m066r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert report["run_id"] == "lambda-m066r-remote-decodilo-vertical-slice"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["remote_command"] == "m066r-command-manifest"
    assert report["remote_command_result"] == "succeeded"
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert len(report["remote_command_stage_results"]) == 3
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert evidence["vertical_slice_status"] == "vertical_slice_success"
    assert evidence["commands_executed"] == 3
    assert evidence["stdout_stored"] is False


def test_m067r_source_bundle_blocks_secret_values(tmp_path):
    root = _minimal_source_project(tmp_path)
    (root / "src" / "decodilo" / "secret_fixture.py").write_text(
        "LAMBDA_API_KEY=abcdefghijklmnopqrstuvwxyz\n",
        encoding="utf-8",
    )

    report = build_lambda_remote_source_bundle(
        project_root=root,
        bundle=tmp_path / "bundle.tar.gz",
        manifest_out=tmp_path / "bundle-manifest.json",
    )

    assert report.secret_scan_passed is False
    assert any(blocker.startswith("secret_") for blocker in report.blockers)
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m067r3_source_bundle_includes_probe_and_excludes_sensitive_artifacts(tmp_path):
    root = _minimal_source_project(tmp_path)
    (root / ".env").write_text("LAMBDA_API_KEY=should-not-upload\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (root / ".pytest_cache").mkdir()
    (root / ".pytest_cache" / "cache.txt").write_text("cache\n", encoding="utf-8")
    (root / "id_ed25519.key").write_text("private-ish\n", encoding="utf-8")
    (root / "lambda-report.json").write_text("{}\n", encoding="utf-8")

    bundle = tmp_path / "decodilo-source-bundle-m067r3.tar.gz"
    manifest = tmp_path / "bundle-manifest.json"
    report = build_lambda_remote_source_bundle(
        project_root=root,
        bundle=bundle,
        manifest_out=manifest,
    )

    assert report.secret_scan_passed is True
    assert report.large_file_scan_passed is True
    import tarfile

    with tarfile.open(bundle, "r:gz") as tar:
        names = set(tar.getnames())
    assert "tools/remote_probe/import_decodilo.py" in names
    assert ".env" not in names
    assert ".git/config" not in names
    assert ".pytest_cache/cache.txt" not in names
    assert "id_ed25519.key" not in names
    assert "lambda-report.json" not in names


def test_m067r_source_bundle_artifact_chain_allows_one_bundle_only(tmp_path):
    paths = _write_m067r_inputs(tmp_path)

    bundle_validation = json.loads(paths["m067r_bundle_validation"].read_text())
    manifest = json.loads(paths["m067r_manifest"].read_text())
    validation = json.loads(paths["m067r_manifest_validation"].read_text())
    plan = json.loads(paths["m067r_plan"].read_text())
    gate = json.loads(paths["m067r_gate"].read_text())
    bridge = json.loads(paths["m067r_bridge"].read_text())

    assert bundle_validation["validation_passed"] is True
    assert bundle_validation["secret_scan_passed"] is True
    assert manifest["milestone"] == "M067R"
    assert manifest["max_remote_commands"] == 7
    assert validation["validation_passed"] is True
    assert plan["plan_status"] == "plan_passed"
    assert plan["max_uploaded_bundles"] == 1
    assert plan["single_source_bundle_upload_allowed"] is True
    assert plan["file_transfer_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["source_bundle_sha256"] == bundle_validation["bundle_sha256"]
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True
    assert bridge["max_uploaded_bundles"] == 1
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m067r_fake_server_uploads_one_bundle_runs_manifest_and_terminates(tmp_path):
    paths = _write_m067r_inputs(tmp_path)
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m067r-source-bundle",
        str(paths["m067r_bundle"]),
        "--m067r-source-bundle-validation",
        str(paths["m067r_bundle_validation"]),
        "--m067r-command-manifest",
        str(paths["m067r_manifest"]),
        "--m067r-manifest-validation",
        str(paths["m067r_manifest_validation"]),
        "--m067r-plan",
        str(paths["m067r_plan"]),
        "--m067r-gate-check",
        str(paths["m067r_gate"]),
        "--m067r-one-shot-arming",
        str(paths["m067r_arming"]),
        "--m067r-reviewer-bridge",
        str(paths["m067r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert report["run_id"] == "lambda-m067r-source-bundle-vertical-slice"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["remote_command"] == "m067r-source-bundle-command-manifest"
    assert report["source_bundle_upload_attempted"] is True
    assert report["source_bundle_upload_succeeded"] is True
    assert report["source_bundle_hash_verified"] is True
    assert report["uploaded_bundles_count"] == 1
    assert report["remote_command_result"] == "succeeded"
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert len(report["remote_command_stage_results"]) == 7
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert evidence["source_bundle_upload_attempted"] is True
    assert evidence["source_bundle_hash_verified"] is True
    assert evidence["commands_executed"] == 7


def test_m068r_fake_server_uploads_dependency_bundle_runs_manifest_and_terminates(
    tmp_path,
):
    paths = _write_m068r_inputs(tmp_path)
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m067r-source-bundle",
        str(paths["m067r_bundle"]),
        "--m067r-source-bundle-validation",
        str(paths["m067r_bundle_validation"]),
        "--m068r-dependency-bundle",
        str(paths["m068r_dep_bundle"]),
        "--m068r-dependency-bundle-validation",
        str(paths["m068r_dep_validation"]),
        "--m067r-command-manifest",
        str(paths["m067r_manifest"]),
        "--m067r-manifest-validation",
        str(paths["m067r_manifest_validation"]),
        "--m067r-plan",
        str(paths["m067r_plan"]),
        "--m067r-gate-check",
        str(paths["m067r_gate"]),
        "--m067r-one-shot-arming",
        str(paths["m067r_arming"]),
        "--m067r-reviewer-bridge",
        str(paths["m067r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert report["run_id"] == "lambda-m068r2-dependency-bundle-vertical-slice"
    assert report["remote_command"] == "m068r-dependency-bundle-command-manifest"
    assert report["uploaded_bundles_count"] == 2
    assert report["source_bundle_hash_verified"] is True
    assert report["dependency_bundle_upload_attempted"] is True
    assert report["dependency_bundle_upload_succeeded"] is True
    assert report["dependency_bundle_hash_verified"] is True
    assert report["local_dependency_install_attempted"] is True
    assert report["local_dependency_install_succeeded"] is True
    assert report["package_install_attempted"] is False
    assert report["downloads_attempted"] is False
    assert report["training_attempted"] is False
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert len(report["remote_command_stage_results"]) == 12
    assert evidence["dependency_bundle_hash_verified"] is True
    assert evidence["commands_executed"] == 12


def test_m068r_default_manifest_includes_full_remaining_vertical_slice(tmp_path):
    policy = tmp_path / "policy.json"
    manifest = tmp_path / "manifest.json"
    validation = tmp_path / "manifest-validation.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    write_lambda_remote_vertical_slice_command_manifest(
        manifest,
        build_lambda_m068r_dependency_bundle_default_manifest(),
    )

    report = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest,
        policy=policy,
    )
    write_lambda_remote_vertical_slice_manifest_validation(validation, report)

    payload = json.loads(manifest.read_text())
    stages = [entry["stage"] for entry in payload["command_entries"]]
    assert report.validation_passed is True
    assert payload["max_remote_commands"] == 12
    assert stages[-5:] == [
        "dependency_install_local_only",
        "decodilo_import_check",
        "decodilo_cli_help_check",
        "decodilo_profile_summary_check",
        "decodilo_ci_profile_report_smoke",
    ]
    smoke = payload["command_entries"][-1]["argv_tokens"]
    assert smoke == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "ci-profile-report",
        "--out",
        "/tmp/decodilo-remote-ci-profile-report.json",
    ]


def test_m068r_records_m067r3_missing_pydantic_failure(tmp_path):
    workdir = tmp_path / "m067r3"
    workdir.mkdir()
    (workdir / "report.json").write_text(
        json.dumps(
            {
                "termination_verified": True,
                "package_install_attempted": False,
                "downloads_attempted": False,
                "training_attempted": False,
            }
        ),
        encoding="utf-8",
    )
    (workdir / "remote-vslice-evidence.json").write_text(
        json.dumps(
            {
                "stage_results": [
                    {"stage": "decodilo_import_check", "passed": True},
                    {"stage": "decodilo_cli_help_check", "passed": False},
                ],
                "stderr_redacted": "ModuleNotFoundError: No module named 'pydantic'",
            }
        ),
        encoding="utf-8",
    )

    record = build_lambda_m067r_dependency_failure_record_from_paths(workdir=workdir)

    assert record.decodilo_import_check_passed is True
    assert record.cli_help_check_attempted is True
    assert record.cli_help_check_passed is False
    assert record.missing_module == "pydantic"
    assert record.failure_type == "missing_runtime_dependency"
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_m068r_inventory_separates_runtime_dependency(tmp_path):
    failure_path = _m068r_failure_fixture(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\ndependencies = ['pydantic>=2,<3', 'numpy>=1.24']\n"
        "[project.optional-dependencies]\ndev = ['pytest>=8']\n",
        encoding="utf-8",
    )

    inventory = build_lambda_runtime_dependency_inventory_from_paths(
        pyproject=pyproject,
        failure_record=failure_path,
    )

    assert inventory.inventory_status == "inventory_built"
    assert inventory.missing_runtime_dependency == "pydantic"
    assert inventory.pydantic_required_for_cli_startup is True
    assert "pytest>=8" in inventory.dev_dependencies
    assert inventory.install_performed is False
    assert inventory.download_performed is False


def test_m068r_bundle_builder_fails_closed_without_compatible_local_artifact(tmp_path):
    inventory_path = tmp_path / "inventory.json"
    write_lambda_runtime_dependency_inventory(
        inventory_path,
        build_lambda_runtime_dependency_inventory_from_paths(
            pyproject=Path("pyproject.toml"),
            failure_record=_m068r_failure_fixture(tmp_path),
        ),
    )

    manifest = build_lambda_dependency_bundle_from_paths(
        inventory=inventory_path,
        bundle=tmp_path / "dependency-bundle.tar.gz",
        manifest_out=tmp_path / "dependency-bundle.manifest.json",
    )
    validation = validate_lambda_dependency_bundle_from_paths(
        bundle=tmp_path / "dependency-bundle.tar.gz",
        manifest=tmp_path / "dependency-bundle.manifest.json",
        inventory=inventory_path,
    )

    if manifest.bundle_status != "bundle_created":
        assert "not_feasible_without_download" in manifest.blockers
        assert validation.validation_passed is False
        assert validation.secret_scan_status == "not_performed_missing_bundle"
        assert validation.launch_ready is False
        assert validation.launch_allowed is False
    else:
        assert validation.validation_passed is True
        assert validation.contains_pydantic is True


def test_m068r_manifest_allows_only_local_no_index_pip_install(tmp_path):
    policy = tmp_path / "policy.json"
    manifest_path = tmp_path / "m068r-manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    manifest = build_lambda_m068r_dependency_bundle_default_manifest()
    write_lambda_remote_vertical_slice_command_manifest(manifest_path, manifest)

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest_path,
        policy=policy,
    )

    assert manifest.milestone == M068R_MILESTONE
    assert validation.validation_passed is True
    assert validation.no_downloads is True
    assert validation.no_internet_install is True
    assert validation.dependency_strategy == "local_wheelhouse_no_index"
    assert validation.no_package_install is True


def test_m068r_manifest_rejects_internet_pip_install(tmp_path):
    policy = tmp_path / "policy.json"
    manifest_path = tmp_path / "m068r-bad-manifest.json"
    write_lambda_remote_vertical_slice_policy(
        policy,
        build_lambda_remote_vertical_slice_policy(),
    )
    entry = LambdaRemoteVerticalSliceCommandEntry(
        stage="dependency_install_or_path_setup",
        exact_command="python3 -m pip install pydantic",
        argv_tokens=["python3", "-m", "pip", "install", "pydantic"],
        failure_stage_if_nonzero="dependency_install_or_path_setup",
    )
    write_lambda_remote_vertical_slice_command_manifest(
        manifest_path,
        LambdaRemoteVerticalSliceCommandManifest(
            milestone=M068R_MILESTONE,
            max_remote_commands=1,
            command_entries=[entry],
        ),
    )

    validation = validate_lambda_remote_vertical_slice_manifest_from_paths(
        manifest=manifest_path,
        policy=policy,
    )

    assert validation.validation_passed is False
    assert any("internet_package_install" in blocker for blocker in validation.blockers)


def test_m071r_fake_server_runs_first_experiment_and_records_artifact_metadata(
    tmp_path,
):
    paths = _write_m068r_inputs(tmp_path)
    commands = [
        ("python_version_check", ["python3", "--version"]),
        ("source_bundle_hash_check", ["sha256sum", M067R_REMOTE_BUNDLE_PATH]),
        (
            "dependency_bundle_hash_check",
            ["sha256sum", M068R_REMOTE_DEPENDENCY_BUNDLE_PATH],
        ),
        ("source_extract_dir", ["mkdir", "-p", M067R_REMOTE_EXTRACT_DIR]),
        (
            "source_bundle_extract",
            ["tar", "-xzf", M067R_REMOTE_BUNDLE_PATH, "-C", M067R_REMOTE_EXTRACT_DIR],
        ),
        (
            "dependency_extract_dir",
            ["mkdir", "-p", M068R_REMOTE_DEPENDENCY_EXTRACT_DIR],
        ),
        (
            "dependency_bundle_extract",
            [
                "tar",
                "-xzf",
                M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
                "-C",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
            ],
        ),
        (
            "dependency_install_local_only",
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
                "--target",
                M068R_REMOTE_RUNTIME_TARGET_DIR,
                "pydantic",
                "beautifulsoup4",
                "numpy",
            ],
        ),
        (
            "decodilo_import_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                M067R_REMOTE_IMPORT_PROBE_PATH,
            ],
        ),
        (
            "decodilo_cli_help_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                "-m",
                "decodilo.cli",
                "--help",
            ],
        ),
        ("first_experiment_command", list(M071R_FIRST_EXPERIMENT_COMMAND)),
    ]
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone=M071R_MILESTONE,
        max_remote_commands=len(commands),
        dependency_strategy="local_wheelhouse",
        command_entries=[
            LambdaRemoteVerticalSliceCommandEntry(
                stage=stage,
                exact_command=render_lambda_remote_vertical_slice_argv(argv),
                argv_tokens=argv,
                timeout_seconds=30,
                failure_stage_if_nonzero=stage,
            )
            for stage, argv in commands
        ],
    )
    write_lambda_remote_vertical_slice_command_manifest(paths["m067r_manifest"], manifest)
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m067r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m067r_manifest"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m067r_plan"],
        build_lambda_remote_dependency_bundle_execution_plan_from_paths(
            discovery_report=paths["live_discovery"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            command_manifest=paths["m067r_manifest"],
            manifest_validation=paths["m067r_manifest_validation"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m067r_gate"],
        build_lambda_remote_dependency_bundle_gate_check_from_paths(
            plan=paths["m067r_plan"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m067r_arming"],
        build_lambda_remote_dependency_bundle_one_shot_arming_from_paths(
            gate_check=paths["m067r_gate"],
            command_manifest=paths["m067r_manifest"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m067r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m067r_arming"],
        ),
    )
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m067r-source-bundle",
        str(paths["m067r_bundle"]),
        "--m067r-source-bundle-validation",
        str(paths["m067r_bundle_validation"]),
        "--m068r-dependency-bundle",
        str(paths["m068r_dep_bundle"]),
        "--m068r-dependency-bundle-validation",
        str(paths["m068r_dep_validation"]),
        "--m067r-command-manifest",
        str(paths["m067r_manifest"]),
        "--m067r-manifest-validation",
        str(paths["m067r_manifest_validation"]),
        "--m067r-plan",
        str(paths["m067r_plan"]),
        "--m067r-gate-check",
        str(paths["m067r_gate"]),
        "--m067r-one-shot-arming",
        str(paths["m067r_arming"]),
        "--m067r-reviewer-bridge",
        str(paths["m067r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    arming = json.loads(paths["m067r_arming"].read_text())
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert arming["arming_status"] == "armed_for_one_shot_m071r_first_experiment"
    assert report["run_id"] == "lambda-m071r-first-experiment"
    assert report["remote_command"] == M071R_MANIFEST_COMMAND_LABEL
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert report["experiment_output_artifact_capture_attempted"] is True
    assert report["experiment_output_artifact_capture_succeeded"] is True
    assert report["experiment_output_artifact_exists"] is True
    assert report["experiment_output_artifact_secret_scan_passed"] is True
    assert evidence["commands_executed"] == len(commands)
    assert evidence["experiment_output_artifact_capture_succeeded"] is True


def test_m073r_fake_server_runs_tiny_smoke_and_records_artifact_metadata(
    tmp_path,
):
    paths = _write_m068r_inputs(tmp_path)
    commands = [
        ("python_version_check", ["python3", "--version"]),
        ("source_bundle_hash_check", ["sha256sum", M073R_REMOTE_BUNDLE_PATH]),
        (
            "dependency_bundle_hash_check",
            ["sha256sum", M068R_REMOTE_DEPENDENCY_BUNDLE_PATH],
        ),
        ("source_extract_dir", ["mkdir", "-p", M067R_REMOTE_EXTRACT_DIR]),
        (
            "source_bundle_extract",
            ["tar", "-xzf", M073R_REMOTE_BUNDLE_PATH, "-C", M067R_REMOTE_EXTRACT_DIR],
        ),
        (
            "dependency_extract_dir",
            ["mkdir", "-p", M068R_REMOTE_DEPENDENCY_EXTRACT_DIR],
        ),
        (
            "dependency_bundle_extract",
            [
                "tar",
                "-xzf",
                M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
                "-C",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
            ],
        ),
        (
            "dependency_install_local_only",
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
                "--target",
                M068R_REMOTE_RUNTIME_TARGET_DIR,
                "pydantic",
                "beautifulsoup4",
                "numpy",
            ],
        ),
        (
            "decodilo_import_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                M067R_REMOTE_IMPORT_PROBE_PATH,
            ],
        ),
        (
            "decodilo_cli_help_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                "-m",
                "decodilo.cli",
                "--help",
            ],
        ),
        ("tiny_smoke_command", list(M073R_TINY_SMOKE_COMMAND)),
    ]
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone=M073R_MILESTONE,
        max_remote_commands=len(commands),
        dependency_strategy="local_wheelhouse",
        command_entries=[
            LambdaRemoteVerticalSliceCommandEntry(
                stage=stage,
                exact_command=render_lambda_remote_vertical_slice_argv(argv),
                argv_tokens=argv,
                timeout_seconds=30,
                failure_stage_if_nonzero=stage,
            )
            for stage, argv in commands
        ],
    )
    write_lambda_remote_vertical_slice_command_manifest(paths["m067r_manifest"], manifest)
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m067r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m067r_manifest"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m067r_plan"],
        build_lambda_remote_dependency_bundle_execution_plan_from_paths(
            discovery_report=paths["live_discovery"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            command_manifest=paths["m067r_manifest"],
            manifest_validation=paths["m067r_manifest_validation"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m067r_gate"],
        build_lambda_remote_dependency_bundle_gate_check_from_paths(
            plan=paths["m067r_plan"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m067r_arming"],
        build_lambda_remote_dependency_bundle_one_shot_arming_from_paths(
            gate_check=paths["m067r_gate"],
            command_manifest=paths["m067r_manifest"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m067r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m067r_arming"],
        ),
    )
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m067r-source-bundle",
        str(paths["m067r_bundle"]),
        "--m067r-source-bundle-validation",
        str(paths["m067r_bundle_validation"]),
        "--m068r-dependency-bundle",
        str(paths["m068r_dep_bundle"]),
        "--m068r-dependency-bundle-validation",
        str(paths["m068r_dep_validation"]),
        "--m067r-command-manifest",
        str(paths["m067r_manifest"]),
        "--m067r-manifest-validation",
        str(paths["m067r_manifest_validation"]),
        "--m067r-plan",
        str(paths["m067r_plan"]),
        "--m067r-gate-check",
        str(paths["m067r_gate"]),
        "--m067r-one-shot-arming",
        str(paths["m067r_arming"]),
        "--m067r-reviewer-bridge",
        str(paths["m067r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    arming = json.loads(paths["m067r_arming"].read_text())
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert arming["arming_status"] == "armed_for_one_shot_m073r_tiny_smoke"
    assert report["run_id"] == "lambda-m073r-tiny-smoke"
    assert report["remote_command"] == M073R_MANIFEST_COMMAND_LABEL
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert report["experiment_output_artifact_capture_attempted"] is True
    assert report["experiment_output_artifact_capture_succeeded"] is True
    assert report["experiment_output_artifact_exists"] is True
    assert report["experiment_output_artifact_secret_scan_passed"] is True
    assert evidence["commands_executed"] == len(commands)
    assert evidence["experiment_output_artifact_capture_succeeded"] is True


def test_m077r_fake_server_runs_synthetic_experiment_and_records_body(
    tmp_path,
):
    paths = _write_m068r_inputs(tmp_path)
    commands = [
        ("python_version_check", ["python3", "--version"]),
        ("source_bundle_hash_check", ["sha256sum", M077R_REMOTE_BUNDLE_PATH]),
        (
            "dependency_bundle_hash_check",
            ["sha256sum", M068R_REMOTE_DEPENDENCY_BUNDLE_PATH],
        ),
        ("source_extract_dir", ["mkdir", "-p", M067R_REMOTE_EXTRACT_DIR]),
        (
            "source_bundle_extract",
            ["tar", "-xzf", M077R_REMOTE_BUNDLE_PATH, "-C", M067R_REMOTE_EXTRACT_DIR],
        ),
        (
            "dependency_extract_dir",
            ["mkdir", "-p", M068R_REMOTE_DEPENDENCY_EXTRACT_DIR],
        ),
        (
            "dependency_bundle_extract",
            [
                "tar",
                "-xzf",
                M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
                "-C",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
            ],
        ),
        (
            "dependency_install_local_only",
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
                "--target",
                M068R_REMOTE_RUNTIME_TARGET_DIR,
                "pydantic",
                "beautifulsoup4",
                "numpy",
            ],
        ),
        (
            "decodilo_import_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                M067R_REMOTE_IMPORT_PROBE_PATH,
            ],
        ),
        (
            "decodilo_cli_help_check",
            [
                "env",
                f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                "python3",
                "-m",
                "decodilo.cli",
                "--help",
            ],
        ),
        ("synthetic_experiment_command", list(M077R_SYNTHETIC_EXPERIMENT_COMMAND)),
    ]
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone=M077R_MILESTONE,
        max_remote_commands=len(commands),
        dependency_strategy="local_wheelhouse",
        command_entries=[
            LambdaRemoteVerticalSliceCommandEntry(
                stage=stage,
                exact_command=render_lambda_remote_vertical_slice_argv(argv),
                argv_tokens=argv,
                timeout_seconds=30,
                failure_stage_if_nonzero=stage,
            )
            for stage, argv in commands
        ],
    )
    write_lambda_remote_vertical_slice_command_manifest(paths["m067r_manifest"], manifest)
    write_lambda_remote_vertical_slice_manifest_validation(
        paths["m067r_manifest_validation"],
        validate_lambda_remote_vertical_slice_manifest_from_paths(
            manifest=paths["m067r_manifest"],
        ),
    )
    write_lambda_remote_vertical_slice_execution_plan(
        paths["m067r_plan"],
        build_lambda_remote_dependency_bundle_execution_plan_from_paths(
            discovery_report=paths["live_discovery"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            command_manifest=paths["m067r_manifest"],
            manifest_validation=paths["m067r_manifest_validation"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_remote_vertical_slice_gate_check(
        paths["m067r_gate"],
        build_lambda_remote_dependency_bundle_gate_check_from_paths(
            plan=paths["m067r_plan"],
        ),
    )
    write_lambda_remote_vertical_slice_one_shot_arming(
        paths["m067r_arming"],
        build_lambda_remote_dependency_bundle_one_shot_arming_from_paths(
            gate_check=paths["m067r_gate"],
            command_manifest=paths["m067r_manifest"],
            source_bundle_validation=paths["m067r_bundle_validation"],
            dependency_bundle_validation=paths["m068r_dep_validation"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_remote_vertical_slice_reviewer_bridge(
        paths["m067r_bridge"],
        build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
            arming=paths["m067r_arming"],
        ),
    )
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m067r-source-bundle",
        str(paths["m067r_bundle"]),
        "--m067r-source-bundle-validation",
        str(paths["m067r_bundle_validation"]),
        "--m068r-dependency-bundle",
        str(paths["m068r_dep_bundle"]),
        "--m068r-dependency-bundle-validation",
        str(paths["m068r_dep_validation"]),
        "--m067r-command-manifest",
        str(paths["m067r_manifest"]),
        "--m067r-manifest-validation",
        str(paths["m067r_manifest_validation"]),
        "--m067r-plan",
        str(paths["m067r_plan"]),
        "--m067r-gate-check",
        str(paths["m067r_gate"]),
        "--m067r-one-shot-arming",
        str(paths["m067r_arming"]),
        "--m067r-reviewer-bridge",
        str(paths["m067r_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    arming = json.loads(paths["m067r_arming"].read_text())
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "remote-vslice-evidence.json").read_text())
    assert (
        arming["arming_status"]
        == "armed_for_one_shot_m077r_first_synthetic_experiment"
    )
    assert report["run_id"] == "lambda-m077r-first-synthetic-experiment"
    assert report["remote_command"] == M077R_MANIFEST_COMMAND_LABEL
    assert report["vertical_slice_status"] == "vertical_slice_success"
    assert report["experiment_output_artifact_capture_attempted"] is True
    assert report["experiment_output_artifact_capture_succeeded"] is True
    assert report["experiment_output_artifact_body_persisted"] is True
    assert report["experiment_output_artifact_body_json"] == {
        "synthetic_experiment_status": "passed"
    }
    assert evidence["commands_executed"] == len(commands)
    assert evidence["experiment_output_artifact_parsed_summary_persisted"] is True


def _m068r_failure_fixture(tmp_path: Path) -> Path:
    workdir = tmp_path / "m067r3-fixture"
    workdir.mkdir(exist_ok=True)
    (workdir / "report.json").write_text(
        json.dumps({"termination_verified": True}),
        encoding="utf-8",
    )
    (workdir / "remote-vslice-evidence.json").write_text(
        json.dumps(
            {
                "stage_results": [
                    {"stage": "decodilo_import_check", "passed": True},
                    {"stage": "decodilo_cli_help_check", "passed": False},
                ],
                "stderr_redacted": "ModuleNotFoundError: No module named 'pydantic'",
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "failure.json"
    write_lambda_m067r_dependency_failure_record(
        output,
        build_lambda_m067r_dependency_failure_record_from_paths(workdir=workdir),
    )
    return output
