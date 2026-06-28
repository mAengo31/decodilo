from __future__ import annotations

import zipfile
from pathlib import Path

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    build_lambda_linux_python310_wheelhouse_plan_from_paths,
    write_lambda_linux_python310_wheelhouse_plan,
)
from decodilo.lambda_cloud.m068w_report import build_lambda_m068w_report_from_paths
from decodilo.lambda_cloud.remote_dependency_bundle import (
    LambdaRuntimeDependencyInventory,
    validate_lambda_dependency_bundle_from_paths,
    write_lambda_dependency_bundle_validation,
    write_lambda_runtime_dependency_inventory,
)
from decodilo.lambda_cloud.wheelhouse_build_policy import (
    build_lambda_wheelhouse_build_policy_from_paths,
    write_lambda_wheelhouse_build_policy,
)
from decodilo.lambda_cloud.wheelhouse_candidate_audit import (
    audit_existing_lambda_wheelhouse_candidates_from_paths,
    write_lambda_wheelhouse_candidate_audit,
)
from decodilo.lambda_cloud.wheelhouse_compatibility_audit import (
    audit_lambda_wheelhouse_compatibility_from_paths,
    write_lambda_wheelhouse_compatibility_audit,
)
from decodilo.lambda_cloud.wheelhouse_manifest import (
    build_lambda_m068w_dependency_bundle_from_paths,
    build_lambda_wheelhouse_manifest_from_paths,
    write_lambda_wheelhouse_manifest,
)
from decodilo.lambda_cloud.wheelhouse_secret_scan import (
    scan_lambda_wheelhouse_secrets_from_paths,
    write_lambda_wheelhouse_secret_scan,
)


def test_m068w_plan_targets_linux_python310_and_excludes_dev_deps(tmp_path: Path) -> None:
    inventory = _write_inventory(tmp_path)

    plan = build_lambda_linux_python310_wheelhouse_plan_from_paths(
        inventory=inventory,
        target_python="3.10",
        target_platform="manylinux2014_x86_64",
    )

    assert plan.plan_status == "plan_built"
    assert plan.target_abi == "cp310"
    assert "pydantic" in plan.required_packages
    assert "pydantic-core" in plan.required_packages
    assert "dev" in plan.excluded_dependency_groups
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_m068w_existing_audit_rejects_macos_and_cp313_wheels(tmp_path: Path) -> None:
    plan_path = _write_plan(tmp_path)
    _write_wheel(tmp_path / "pydantic_core-2.41.5-cp313-cp313-macosx_14_0_arm64.whl")

    audit = audit_existing_lambda_wheelhouse_candidates_from_paths(
        plan=plan_path,
        search_paths=[tmp_path],
    )

    assert audit.audit_status == "not_found"
    assert audit.incompatible_wheels
    assert any("macos_wheel_rejected" in item.blockers for item in audit.incompatible_wheels)
    assert any("python_313_abi_rejected" in item.blockers for item in audit.incompatible_wheels)
    assert audit.launch_ready is False
    assert audit.launch_allowed is False


def test_m068w_existing_audit_accepts_manylinux_cp310_wheelhouse(tmp_path: Path) -> None:
    plan_path = _write_plan(tmp_path)
    _write_complete_wheelhouse(tmp_path)

    audit = audit_existing_lambda_wheelhouse_candidates_from_paths(
        plan=plan_path,
        search_paths=[tmp_path],
    )

    assert audit.audit_status == "compatible_wheelhouse_found"
    assert not audit.missing_packages


def test_m068w_build_policy_blocks_without_operator_download_approval(
    tmp_path: Path,
) -> None:
    plan_path = _write_plan(tmp_path)
    audit_path = tmp_path / "audit.json"
    write_lambda_wheelhouse_candidate_audit(
        audit_path,
        audit_existing_lambda_wheelhouse_candidates_from_paths(
            plan=plan_path,
            search_paths=[tmp_path / "empty"],
        ),
    )

    policy = build_lambda_wheelhouse_build_policy_from_paths(
        plan=plan_path,
        existing_audit=audit_path,
    )
    approved = build_lambda_wheelhouse_build_policy_from_paths(
        plan=plan_path,
        existing_audit=audit_path,
        approve_controlled_local_wheel_download=True,
    )

    assert policy.policy_status == "blocked_needs_operator_approval_for_local_wheel_download"
    assert approved.policy_status == "approved_controlled_local_wheel_download"
    assert "--only-binary=:all:" in approved.download_command_preview
    assert approved.no_local_install is True
    assert approved.no_lambda_side_internet is True


def test_m068w_manifest_secret_scan_compatibility_bundle_and_report(
    tmp_path: Path,
) -> None:
    plan_path = _write_plan(tmp_path)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    _write_complete_wheelhouse(wheelhouse)
    manifest_path = tmp_path / "wheelhouse-manifest.json"
    secret_scan_path = tmp_path / "secret-scan.json"
    compatibility_path = tmp_path / "compatibility.json"
    bundle_path = tmp_path / "dependency-bundle.tar.gz"
    bundle_manifest_path = tmp_path / "dependency-bundle.manifest.json"
    bundle_validation_path = tmp_path / "bundle-validation.json"
    audit_path = tmp_path / "audit.json"
    policy_path = tmp_path / "policy.json"

    manifest = build_lambda_wheelhouse_manifest_from_paths(
        wheelhouse_dir=wheelhouse,
        plan=plan_path,
        out=manifest_path,
        download_used=True,
        internet_download_used=True,
    )
    write_lambda_wheelhouse_manifest(manifest_path, manifest)
    scan = scan_lambda_wheelhouse_secrets_from_paths(
        wheelhouse_dir=wheelhouse,
        manifest=manifest_path,
    )
    write_lambda_wheelhouse_secret_scan(secret_scan_path, scan)
    compatibility = audit_lambda_wheelhouse_compatibility_from_paths(
        manifest=manifest_path,
    )
    write_lambda_wheelhouse_compatibility_audit(compatibility_path, compatibility)
    bundle_manifest = build_lambda_m068w_dependency_bundle_from_paths(
        wheelhouse_dir=wheelhouse,
        wheelhouse_manifest=manifest_path,
        secret_scan=secret_scan_path,
        compatibility_audit=compatibility_path,
        bundle=bundle_path,
        manifest_out=bundle_manifest_path,
    )
    validation = validate_lambda_dependency_bundle_from_paths(
        bundle=bundle_path,
        manifest=bundle_manifest_path,
        inventory=_write_inventory(tmp_path),
    )
    write_lambda_dependency_bundle_validation(bundle_validation_path, validation)
    write_lambda_wheelhouse_candidate_audit(
        audit_path,
        audit_existing_lambda_wheelhouse_candidates_from_paths(
            plan=plan_path,
            search_paths=[wheelhouse],
        ),
    )
    write_lambda_wheelhouse_build_policy(
        policy_path,
        build_lambda_wheelhouse_build_policy_from_paths(
            plan=plan_path,
            existing_audit=audit_path,
        ),
    )
    report = build_lambda_m068w_report_from_paths(
        plan=plan_path,
        existing_audit=audit_path,
        build_policy=policy_path,
        wheelhouse_manifest=manifest_path,
        secret_scan=secret_scan_path,
        compatibility_audit=compatibility_path,
        bundle_validation=bundle_validation_path,
    )

    assert manifest.manifest_status == "manifest_built"
    assert scan.secret_scan_passed is True
    assert compatibility.compatibility_audit_passed is True
    assert bundle_manifest.bundle_status == "bundle_created"
    assert validation.validation_passed is True
    assert validation.contains_pydantic is True
    assert validation.internet_download_used is True
    assert report.m068r_retry_ready is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m068w_secret_scan_rejects_private_key_material(tmp_path: Path) -> None:
    plan_path = _write_plan(tmp_path)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    _write_wheel(
        wheelhouse / "pydantic-2.12.5-py3-none-any.whl",
        {"pydantic-2.12.5.dist-info/METADATA": "-----BEGIN PRIVATE KEY-----\n"},
    )
    manifest_path = tmp_path / "manifest.json"
    build_lambda_wheelhouse_manifest_from_paths(
        wheelhouse_dir=wheelhouse,
        plan=plan_path,
        out=manifest_path,
    )

    scan = scan_lambda_wheelhouse_secrets_from_paths(
        wheelhouse_dir=wheelhouse,
        manifest=manifest_path,
    )

    assert scan.secret_scan_passed is False
    assert any("private_key_material" in blocker for blocker in scan.blockers)


def test_m068w_secret_scan_allows_wheel_pycache_entries(tmp_path: Path) -> None:
    plan_path = _write_plan(tmp_path)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    _write_wheel(
        wheelhouse / "numpy-2.2.6-cp310-cp310-manylinux2014_x86_64.whl",
        {"numpy/distutils/__pycache__/conv_template.cpython-310.pyc": "bytecode"},
    )
    manifest_path = tmp_path / "manifest.json"
    build_lambda_wheelhouse_manifest_from_paths(
        wheelhouse_dir=wheelhouse,
        plan=plan_path,
        out=manifest_path,
    )

    scan = scan_lambda_wheelhouse_secrets_from_paths(
        wheelhouse_dir=wheelhouse,
        manifest=manifest_path,
    )

    assert not any("__pycache__" in blocker for blocker in scan.blockers)


def _write_inventory(tmp_path: Path) -> Path:
    path = tmp_path / "inventory.json"
    write_lambda_runtime_dependency_inventory(
        path,
        LambdaRuntimeDependencyInventory(
            inventory_status="inventory_built",
            runtime_dependencies=[
                "beautifulsoup4>=4.12,<5",
                "numpy>=1.24",
                "pydantic>=2,<3",
            ],
            dev_dependencies=["pytest>=8", "ruff>=0.5"],
            missing_runtime_dependency="pydantic",
            pydantic_required_for_cli_startup=True,
        ),
    )
    return path


def _write_plan(tmp_path: Path) -> Path:
    path = tmp_path / "plan.json"
    write_lambda_linux_python310_wheelhouse_plan(
        path,
        build_lambda_linux_python310_wheelhouse_plan_from_paths(
            inventory=_write_inventory(tmp_path),
            target_python="3.10",
            target_platform="manylinux2014_x86_64",
        ),
    )
    return path


def _write_complete_wheelhouse(path: Path) -> None:
    for filename in (
        "annotated_types-0.7.0-py3-none-any.whl",
        "beautifulsoup4-4.14.2-py3-none-any.whl",
        "numpy-2.2.6-cp310-cp310-manylinux2014_x86_64.whl",
        "pydantic-2.12.5-py3-none-any.whl",
        "pydantic_core-2.41.5-cp310-cp310-manylinux2014_x86_64.whl",
        "typing_extensions-4.15.0-py3-none-any.whl",
        "typing_inspection-0.4.2-py3-none-any.whl",
    ):
        _write_wheel(path / filename)


def _write_wheel(path: Path, extra_files: dict[str, str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dist_info = path.name[:-4].split("-", 1)[0] + "-0.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist_info}/METADATA", "Name: fixture\n")
        archive.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\n")
        for name, content in (extra_files or {}).items():
            archive.writestr(name, content)
