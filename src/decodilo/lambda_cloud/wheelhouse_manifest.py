"""Manifesting and bundling for M068W dependency wheelhouses."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    load_lambda_linux_python310_wheelhouse_plan,
)
from decodilo.lambda_cloud.remote_dependency_bundle import (
    LambdaDependencyBundleManifest,
    write_lambda_dependency_bundle_manifest,
)
from decodilo.lambda_cloud.wheelhouse_build_policy import (
    load_lambda_wheelhouse_build_policy,
)


class LambdaWheelhousePackageFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    package_name: str
    version: str
    sha256: str
    bytes: int
    python_tag: str
    abi_tag: str
    platform_tag: str


class LambdaWheelhouseManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    manifest_status: Literal["manifest_built", "blocked"]
    wheelhouse_dir: str
    package_files: list[LambdaWheelhousePackageFile] = Field(default_factory=list)
    package_names: list[str] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)
    total_bytes: int = 0
    target_python: str
    target_platform: str
    target_abi: str
    download_used: bool = False
    internet_download_used: bool = False
    local_only_for_lambda: bool = True
    download_command: list[str] = Field(default_factory=list)
    pip_returncode: int | None = None
    pip_stdout_bytes: int = 0
    pip_stderr_bytes: int = 0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaWheelhouseManifest:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("wheelhouse manifest must not enable launch or spend")
        if not self.local_only_for_lambda:
            raise ValueError("future Lambda install source must stay local-only")
        if self.manifest_status == "manifest_built" and self.blockers:
            raise ValueError("passing wheelhouse manifest cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def download_lambda_m068w_wheelhouse_from_paths(
    *,
    policy: str | Path,
    plan: str | Path,
    wheelhouse_dir: str | Path,
    out: str | Path,
) -> LambdaWheelhouseManifest:
    build_policy = load_lambda_wheelhouse_build_policy(policy)
    wheelhouse_plan = load_lambda_linux_python310_wheelhouse_plan(plan)
    target_dir = Path(wheelhouse_dir)
    blockers = [*build_policy.blockers, *wheelhouse_plan.blockers]
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--implementation",
        wheelhouse_plan.target_implementation,
        "--python-version",
        wheelhouse_plan.target_python.replace(".", ""),
        "--abi",
        wheelhouse_plan.target_abi,
        "--platform",
        wheelhouse_plan.target_platform,
        "--dest",
        str(target_dir),
        *wheelhouse_plan.download_requirements,
    ]
    if build_policy.policy_status != "approved_controlled_local_wheel_download":
        blockers.append("controlled_local_wheel_download_not_approved")
        report = _manifest_from_dir(
            wheelhouse_dir=target_dir,
            plan=wheelhouse_plan,
            download_used=False,
            internet_download_used=False,
            download_command=command,
            pip_returncode=None,
            pip_stdout_bytes=0,
            pip_stderr_bytes=0,
            blockers=blockers,
        )
        write_lambda_wheelhouse_manifest(out, report)
        return report
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=False,
    )
    if proc.returncode != 0:
        blockers.append(f"pip_download_failed:{proc.returncode}")
    if any(path.suffix != ".whl" for path in target_dir.iterdir() if path.is_file()):
        blockers.append("download_produced_non_wheel_artifact")
    report = _manifest_from_dir(
        wheelhouse_dir=target_dir,
        plan=wheelhouse_plan,
        download_used=True,
        internet_download_used=True,
        download_command=command,
        pip_returncode=proc.returncode,
        pip_stdout_bytes=len(proc.stdout or b""),
        pip_stderr_bytes=len(proc.stderr or b""),
        blockers=blockers,
    )
    write_lambda_wheelhouse_manifest(out, report)
    return report


def build_lambda_wheelhouse_manifest_from_paths(
    *,
    wheelhouse_dir: str | Path,
    plan: str | Path,
    out: str | Path,
    download_used: bool = False,
    internet_download_used: bool = False,
) -> LambdaWheelhouseManifest:
    wheelhouse_plan = load_lambda_linux_python310_wheelhouse_plan(plan)
    report = _manifest_from_dir(
        wheelhouse_dir=Path(wheelhouse_dir),
        plan=wheelhouse_plan,
        download_used=download_used,
        internet_download_used=internet_download_used,
        download_command=[],
        pip_returncode=None,
        pip_stdout_bytes=0,
        pip_stderr_bytes=0,
        blockers=list(wheelhouse_plan.blockers),
    )
    write_lambda_wheelhouse_manifest(out, report)
    return report


def build_lambda_m068w_dependency_bundle_from_paths(
    *,
    wheelhouse_dir: str | Path,
    wheelhouse_manifest: str | Path,
    secret_scan: str | Path,
    compatibility_audit: str | Path,
    bundle: str | Path,
    manifest_out: str | Path,
) -> LambdaDependencyBundleManifest:
    from decodilo.lambda_cloud.wheelhouse_compatibility_audit import (
        load_lambda_wheelhouse_compatibility_audit,
    )
    from decodilo.lambda_cloud.wheelhouse_secret_scan import (
        load_lambda_wheelhouse_secret_scan,
    )

    man = load_lambda_wheelhouse_manifest(wheelhouse_manifest)
    scan = load_lambda_wheelhouse_secret_scan(secret_scan)
    compat = load_lambda_wheelhouse_compatibility_audit(compatibility_audit)
    bundle_path = Path(bundle)
    blockers = [*man.blockers, *scan.blockers, *compat.blockers]
    if man.manifest_status != "manifest_built":
        blockers.append("wheelhouse_manifest_not_built")
    if not scan.secret_scan_passed:
        blockers.append("wheelhouse_secret_scan_not_passed")
    if not compat.compatibility_audit_passed:
        blockers.append("wheelhouse_compatibility_audit_not_passed")
    if blockers:
        report = LambdaDependencyBundleManifest(
            milestone="M068W",
            bundle_status="blocked",
            bundle_path=str(bundle_path),
            dependency_items=man.package_names,
            versions=man.versions,
            source="local_wheelhouse",
            secret_scan_passed=False,
            internet_download_used=man.internet_download_used,
            blockers=sorted(set(blockers)),
        )
        write_lambda_dependency_bundle_manifest(manifest_out, report)
        return report
    if bundle_path.exists():
        bundle_path.unlink()
    with tarfile.open(bundle_path, "w:gz") as tar:
        for path in sorted(Path(wheelhouse_dir).iterdir()):
            if path.is_file() and path.suffix == ".whl":
                tar.add(path, arcname=path.name)
    sha = _sha256_file(bundle_path)
    report = LambdaDependencyBundleManifest(
        milestone="M068W",
        bundle_status="bundle_created",
        bundle_path=str(bundle_path),
        dependency_items=man.package_names,
        versions=man.versions,
        source="local_wheelhouse",
        total_bytes=bundle_path.stat().st_size,
        sha256=sha,
        secret_scan_passed=True,
        platform_compatibility_notes=compat.compatibility_notes,
        internet_download_used=man.internet_download_used,
        warnings=[
            "bundle contains wheelhouse files only; future Lambda install must use --no-index"
        ],
    )
    write_lambda_dependency_bundle_manifest(manifest_out, report)
    return report


def load_lambda_wheelhouse_manifest(path: str | Path) -> LambdaWheelhouseManifest:
    return LambdaWheelhouseManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_wheelhouse_manifest(path: str | Path, report: LambdaWheelhouseManifest) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _manifest_from_dir(
    *,
    wheelhouse_dir: Path,
    plan,
    download_used: bool,
    internet_download_used: bool,
    download_command: list[str],
    pip_returncode: int | None,
    pip_stdout_bytes: int,
    pip_stderr_bytes: int,
    blockers: list[str],
) -> LambdaWheelhouseManifest:
    files: list[LambdaWheelhousePackageFile] = []
    if not wheelhouse_dir.exists():
        blockers.append("wheelhouse_dir_missing")
    else:
        for path in sorted(wheelhouse_dir.iterdir()):
            if not path.is_file():
                continue
            parsed = _parse_wheel_filename(path.name)
            if parsed is None:
                blockers.append(f"wheel_filename_unparseable:{path.name}")
                continue
            package, version, python_tag, abi_tag, platform_tag = parsed
            files.append(
                LambdaWheelhousePackageFile(
                    filename=path.name,
                    package_name=package.replace("_", "-").lower(),
                    version=version,
                    sha256=_sha256_file(path),
                    bytes=path.stat().st_size,
                    python_tag=python_tag,
                    abi_tag=abi_tag,
                    platform_tag=platform_tag,
                )
            )
    package_names = sorted({file.package_name for file in files})
    missing = sorted(package for package in plan.required_packages if package not in package_names)
    blockers.extend(f"wheelhouse_missing_package:{package}" for package in missing)
    return LambdaWheelhouseManifest(
        manifest_status="manifest_built" if not blockers else "blocked",
        wheelhouse_dir=str(wheelhouse_dir),
        package_files=files,
        package_names=package_names,
        versions={file.package_name: file.version for file in files},
        total_bytes=sum(file.bytes for file in files),
        target_python=plan.target_python,
        target_platform=plan.target_platform,
        target_abi=plan.target_abi,
        download_used=download_used,
        internet_download_used=internet_download_used,
        download_command=download_command,
        pip_returncode=pip_returncode,
        pip_stdout_bytes=pip_stdout_bytes,
        pip_stderr_bytes=pip_stderr_bytes,
        blockers=sorted(set(blockers)),
        warnings=[
            "wheelhouse manifest is local-only and does not install packages",
            "future Lambda install must use this local bundle with --no-index",
        ],
    )


def _parse_wheel_filename(filename: str) -> tuple[str, str, str, str, str] | None:
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return None
    return parts[0], parts[1], parts[-3], parts[-2], parts[-1]


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
