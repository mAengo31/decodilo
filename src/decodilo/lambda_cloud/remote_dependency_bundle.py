"""Offline dependency-bundle planning for M068R remote vertical slices."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import shutil
import tarfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py310 fallback
    tomllib = None  # type: ignore[assignment]

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M067R_REMOTE_BUNDLE_PATH,
    M067R_REMOTE_EXTRACT_DIR,
    M067R_REMOTE_IMPORT_PROBE_PATH,
    M068R_MILESTONE,
    M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
    M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
    M068R_REMOTE_RUNTIME_TARGET_DIR,
    M081R_DILOCO_SMOKE_COMMAND,
    M081R_MILESTONE,
    M081R_REMOTE_BUNDLE_PATH,
    M083R_DILOCO_OPTIMIZER_SMOKE_COMMAND,
    M083R_MILESTONE,
    M083R_REMOTE_BUNDLE_PATH,
    M085R_INTEGRATED_DILOCO_SMOKE_COMMAND,
    M085R_MILESTONE,
    M085R_REMOTE_BUNDLE_PATH,
    M087R_MILESTONE,
    M087R_PARAMETER_FRAGMENT_SMOKE_COMMAND,
    M087R_REMOTE_BUNDLE_PATH,
    M089R_BOUNDED_DILOCO_EXPERIMENT_COMMAND,
    M089R_MILESTONE,
    M089R_REMOTE_BUNDLE_PATH,
    M093R_MILESTONE,
    M093R_REMOTE_BUNDLE_PATH,
    M093R_TINY_REAL_TRAINING_SMOKE_COMMAND,
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    render_lambda_remote_vertical_slice_argv,
)

REMOTE_DEPENDENCY_BUNDLE_PATH = M068R_REMOTE_DEPENDENCY_BUNDLE_PATH
REMOTE_DEPENDENCY_EXTRACT_DIR = M068R_REMOTE_DEPENDENCY_EXTRACT_DIR
REMOTE_RUNTIME_TARGET_DIR = M068R_REMOTE_RUNTIME_TARGET_DIR
TARGET_REMOTE_PYTHON = "3.10"


class LambdaM067RDependencyFailureRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M067R3"
    decodilo_import_check_passed: bool
    cli_help_check_attempted: bool
    cli_help_check_passed: bool
    missing_module: str | None = None
    failure_type: Literal[
        "missing_runtime_dependency",
        "other_cli_startup_failure",
        "not_a_dependency_failure",
    ]
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaM067RDependencyFailureRecord:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("dependency failure record must not enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRuntimeDependencyInventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    inventory_status: Literal["inventory_built", "blocked"]
    runtime_dependencies: list[str] = Field(default_factory=list)
    dev_dependencies: list[str] = Field(default_factory=list)
    missing_runtime_dependency: str | None = None
    pydantic_required_for_cli_startup: bool = False
    install_performed: bool = False
    download_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_inventory(self) -> LambdaRuntimeDependencyInventory:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.install_performed
            or self.download_performed
        ):
            raise ValueError("dependency inventory must be offline and non-launching")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaDependencyBundleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    milestone: str = "M068R"
    bundle_status: Literal["bundle_created", "not_feasible_without_download", "blocked"]
    bundle_path: str
    dependency_items: list[str] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)
    source: str | None = None
    total_bytes: int = 0
    sha256: str = "0" * 64
    secret_scan_passed: bool = False
    platform_compatibility_notes: list[str] = Field(default_factory=list)
    internet_download_used: bool = False
    package_install_performed_locally: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_manifest(self) -> LambdaDependencyBundleManifest:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.package_install_performed_locally
        ):
            raise ValueError("dependency bundle manifest violates offline constraints")
        if self.bundle_status == "bundle_created" and (
            self.blockers or not self.secret_scan_passed or len(self.sha256) != 64
        ):
            raise ValueError("created dependency bundle cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaDependencyBundleValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068R"
    validation_passed: bool
    bundle_path: str
    bundle_sha256: str
    contains_pydantic: bool
    dependency_strategy: str | None = None
    secret_scan_passed: bool
    secret_scan_status: Literal[
        "passed",
        "failed",
        "not_performed_missing_bundle",
        "not_performed_bundle_not_created",
    ]
    internet_download_used: bool = False
    max_uploaded_bundles: int = 2
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_validation(self) -> LambdaDependencyBundleValidation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.max_uploaded_bundles != 2
        ):
            raise ValueError("dependency bundle validation violates M068R constraints")
        if self.validation_passed and self.blockers:
            raise ValueError("passing dependency bundle validation cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m067r_dependency_failure_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaM067RDependencyFailureRecord:
    workdir_path = Path(workdir)
    report = json.loads((workdir_path / "report.json").read_text(encoding="utf-8"))
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    stages = evidence.get("stage_results") or report.get("remote_command_stage_results") or []
    stage_map = {stage.get("stage"): stage for stage in stages if isinstance(stage, dict)}
    stderr = str(evidence.get("stderr_redacted") or "")
    missing = _missing_module_from_stderr(stderr)
    final_instance_count, final_unmanaged_count = _m067r3_final_counts()
    import_passed = bool(stage_map.get("decodilo_import_check", {}).get("passed"))
    cli_attempted = "decodilo_cli_help_check" in stage_map
    cli_passed = bool(stage_map.get("decodilo_cli_help_check", {}).get("passed"))
    failure_type: Literal[
        "missing_runtime_dependency",
        "other_cli_startup_failure",
        "not_a_dependency_failure",
    ]
    if missing:
        failure_type = "missing_runtime_dependency"
    elif cli_attempted and not cli_passed:
        failure_type = "other_cli_startup_failure"
    else:
        failure_type = "not_a_dependency_failure"
    blockers = []
    if not report.get("termination_verified"):
        blockers.append("m067r3_termination_not_verified")
    return LambdaM067RDependencyFailureRecord(
        decodilo_import_check_passed=import_passed,
        cli_help_check_attempted=cli_attempted,
        cli_help_check_passed=cli_passed,
        missing_module=missing,
        failure_type=failure_type,
        package_install_attempted=bool(report.get("package_install_attempted")),
        download_attempted=bool(report.get("downloads_attempted")),
        training_attempted=bool(report.get("training_attempted")),
        termination_verified=bool(report.get("termination_verified")),
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        blockers=blockers,
        warnings=["M067R3 dependency failure record is offline and non-launching"],
    )


def build_lambda_runtime_dependency_inventory_from_paths(
    *,
    pyproject: str | Path,
    failure_record: str | Path,
) -> LambdaRuntimeDependencyInventory:
    record = load_lambda_m067r_dependency_failure_record(failure_record)
    runtime, dev = _read_pyproject_dependencies(pyproject)
    blockers = []
    if record.failure_type != "missing_runtime_dependency":
        blockers.append("m067r3_missing_dependency_failure_required")
    missing = record.missing_module
    pydantic_required = any(dep.lower().startswith("pydantic") for dep in runtime)
    if missing == "pydantic" and not pydantic_required:
        blockers.append("pydantic_missing_but_not_declared_runtime_dependency")
    return LambdaRuntimeDependencyInventory(
        inventory_status="inventory_built" if not blockers else "blocked",
        runtime_dependencies=runtime,
        dev_dependencies=dev,
        missing_runtime_dependency=missing,
        pydantic_required_for_cli_startup=pydantic_required,
        blockers=blockers,
        warnings=["dependency inventory did not install or download packages"],
    )


def build_lambda_dependency_bundle_from_paths(
    *,
    inventory: str | Path,
    bundle: str | Path,
    manifest_out: str | Path,
) -> LambdaDependencyBundleManifest:
    inv = load_lambda_runtime_dependency_inventory(inventory)
    bundle_path = Path(bundle)
    manifest_path = Path(manifest_out)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    blockers = list(inv.blockers)
    notes: list[str] = []
    items = ["pydantic"]
    versions: dict[str, str] = {}
    package_roots: list[Path] = []
    for package in _runtime_package_closure(items):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            blockers.append(f"local_package_missing:{package}")
            continue
        roots = _package_paths(package)
        if not roots:
            blockers.append(f"local_package_path_missing:{package}")
            continue
        package_roots.extend(roots)
    incompatible = _incompatibility_notes(package_roots)
    notes.extend(incompatible)
    if incompatible:
        blockers.append("compatible_local_dependency_artifact_not_found:pydantic")
        blockers.append("not_feasible_without_download")
    if blockers:
        report = LambdaDependencyBundleManifest(
            bundle_status="not_feasible_without_download"
            if "not_feasible_without_download" in blockers
            else "blocked",
            bundle_path=str(bundle_path),
            dependency_items=sorted(set(items)),
            versions=versions,
            source="local_site_packages_copy",
            secret_scan_passed=False,
            platform_compatibility_notes=notes,
            blockers=sorted(set(blockers)),
            warnings=[
                "No internet download was attempted.",
                "M068R must stop before launch unless validation passes.",
            ],
        )
        write_lambda_dependency_bundle_manifest(manifest_path, report)
        return report
    if bundle_path.exists():
        bundle_path.unlink()
    staging = bundle_path.with_suffix("").with_name(bundle_path.stem + "-staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    total = 0
    bundle_blockers: list[str] = []
    for root in package_roots:
        target = staging / root.name
        if root.is_dir():
            shutil.copytree(root, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(root, target)
        total += _path_total_bytes(target)
    for path in staging.rglob("*"):
        if path.is_file():
            hits = _secret_value_hits(path)
            bundle_blockers.extend(f"secret_{hit}_in_{path.name}" for hit in hits)
    if bundle_blockers:
        shutil.rmtree(staging)
        report = LambdaDependencyBundleManifest(
            bundle_status="blocked",
            bundle_path=str(bundle_path),
            dependency_items=sorted(set(items)),
            versions=versions,
            source="local_site_packages_copy",
            total_bytes=total,
            secret_scan_passed=False,
            platform_compatibility_notes=notes,
            blockers=sorted(set(bundle_blockers)),
        )
        write_lambda_dependency_bundle_manifest(manifest_path, report)
        return report
    with tarfile.open(bundle_path, "w:gz") as tar:
        for child in sorted(staging.iterdir()):
            tar.add(child, arcname=child.name)
    shutil.rmtree(staging)
    sha = _sha256_file(bundle_path)
    report = LambdaDependencyBundleManifest(
        bundle_status="bundle_created",
        bundle_path=str(bundle_path),
        dependency_items=sorted(set(items)),
        versions=versions,
        source="local_site_packages_copy",
        total_bytes=total,
        sha256=sha,
        secret_scan_passed=True,
        platform_compatibility_notes=notes or ["local package copy is pure Python"],
        warnings=["dependency bundle was built from already-installed local artifacts"],
    )
    write_lambda_dependency_bundle_manifest(manifest_path, report)
    return report


def validate_lambda_dependency_bundle_from_paths(
    *,
    bundle: str | Path,
    manifest: str | Path,
    inventory: str | Path,
) -> LambdaDependencyBundleValidation:
    inv = load_lambda_runtime_dependency_inventory(inventory)
    man = load_lambda_dependency_bundle_manifest(manifest)
    bundle_path = Path(bundle)
    blockers = [*inv.blockers, *man.blockers]
    actual_sha = "0" * 64
    contains_pydantic = False
    contains_pydantic_core = False
    if not bundle_path.is_file():
        blockers.append("dependency_bundle_missing")
    else:
        actual_sha = _sha256_file(bundle_path)
        if actual_sha != man.sha256:
            blockers.append("dependency_bundle_hash_mismatch")
        try:
            with tarfile.open(bundle_path, "r:gz") as tar:
                names = [member.name for member in tar.getmembers()]
            contains_pydantic = any(
                name.startswith("pydantic/") or _wheel_name_matches(name, "pydantic")
                for name in names
            )
            contains_pydantic_core = any(
                name.startswith("pydantic_core/")
                or _wheel_name_matches(name, "pydantic-core")
                for name in names
            )
            if any(_dependency_member_forbidden(name) for name in names):
                blockers.append("dependency_bundle_contains_forbidden_path")
        except tarfile.TarError:
            blockers.append("dependency_bundle_tar_unreadable")
    if man.bundle_status != "bundle_created":
        blockers.append(f"dependency_bundle_not_created:{man.bundle_status}")
    if not bundle_path.is_file():
        secret_scan_status: Literal[
            "passed",
            "failed",
            "not_performed_missing_bundle",
            "not_performed_bundle_not_created",
        ] = "not_performed_missing_bundle"
        blockers.append("dependency_bundle_secret_scan_not_performed_missing_bundle")
    elif man.bundle_status != "bundle_created":
        secret_scan_status = "not_performed_bundle_not_created"
        blockers.append("dependency_bundle_secret_scan_not_performed_bundle_not_created")
    elif man.secret_scan_passed:
        secret_scan_status = "passed"
    else:
        secret_scan_status = "failed"
        blockers.append("dependency_bundle_secret_scan_failed")
    if man.internet_download_used and man.source != "local_wheelhouse":
        blockers.append("dependency_bundle_used_internet_download")
    if not contains_pydantic:
        blockers.append("dependency_bundle_missing_pydantic")
    if man.source == "local_wheelhouse" and not contains_pydantic_core:
        blockers.append("dependency_bundle_missing_pydantic_core")
    return LambdaDependencyBundleValidation(
        validation_passed=not blockers,
        bundle_path=str(bundle_path),
        bundle_sha256=actual_sha,
        contains_pydantic=contains_pydantic,
        dependency_strategy=man.source,
        secret_scan_passed=man.secret_scan_passed,
        secret_scan_status=secret_scan_status,
        internet_download_used=man.internet_download_used,
        blockers=sorted(set(blockers)),
        warnings=[
            "dependency bundle validation is local-only and non-launching",
            *man.warnings,
        ],
    )


def build_lambda_m068r_dependency_bundle_default_manifest(
    *,
    use_wheelhouse_install: bool = True,
    milestone: str = M068R_MILESTONE,
) -> LambdaRemoteVerticalSliceCommandManifest:
    runtime_path = f"{REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src"
    remote_source_bundle_path = (
        M093R_REMOTE_BUNDLE_PATH
        if milestone == M093R_MILESTONE
        else M089R_REMOTE_BUNDLE_PATH
        if milestone == M089R_MILESTONE
        else M087R_REMOTE_BUNDLE_PATH
        if milestone == M087R_MILESTONE
        else M085R_REMOTE_BUNDLE_PATH
        if milestone == M085R_MILESTONE
        else M083R_REMOTE_BUNDLE_PATH
        if milestone == M083R_MILESTONE
        else M081R_REMOTE_BUNDLE_PATH
        if milestone == M081R_MILESTONE
        else M067R_REMOTE_BUNDLE_PATH
    )
    commands: list[tuple[str, list[str]]] = [
        ("python_version_check", ["python3", "--version"]),
        ("source_bundle_hash_check", ["sha256sum", remote_source_bundle_path]),
        ("dependency_bundle_hash_check", ["sha256sum", REMOTE_DEPENDENCY_BUNDLE_PATH]),
        ("source_extract_dir", ["mkdir", "-p", M067R_REMOTE_EXTRACT_DIR]),
        (
            "source_bundle_extract",
            ["tar", "-xzf", remote_source_bundle_path, "-C", M067R_REMOTE_EXTRACT_DIR],
        ),
        ("dependency_extract_dir", ["mkdir", "-p", REMOTE_DEPENDENCY_EXTRACT_DIR]),
        (
            "dependency_bundle_extract",
            [
                "tar",
                "-xzf",
                REMOTE_DEPENDENCY_BUNDLE_PATH,
                "-C",
                REMOTE_DEPENDENCY_EXTRACT_DIR,
            ],
        ),
    ]
    if use_wheelhouse_install:
        commands.append(
            (
                "dependency_install_local_only",
                [
                    "python3",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    REMOTE_DEPENDENCY_EXTRACT_DIR,
                    "--target",
                    REMOTE_RUNTIME_TARGET_DIR,
                    "pydantic",
                    "beautifulsoup4",
                    "numpy",
                ],
            )
        )
    else:
        runtime_path = f"{REMOTE_DEPENDENCY_EXTRACT_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src"
    commands.extend(
        [
            (
                "decodilo_import_check",
                [
                    "env",
                    f"PYTHONPATH={runtime_path}",
                    "python3",
                    M067R_REMOTE_IMPORT_PROBE_PATH,
                ],
            ),
            (
                "decodilo_cli_help_check",
                [
                    "env",
                    f"PYTHONPATH={runtime_path}",
                    "python3",
                    "-m",
                    "decodilo.cli",
                    "--help",
                ],
            ),
        ]
    )
    if milestone == M081R_MILESTONE:
        commands.append(("diloco_smoke_command", list(M081R_DILOCO_SMOKE_COMMAND)))
    elif milestone == M083R_MILESTONE:
        commands.append(
            (
                "diloco_optimizer_smoke_command",
                list(M083R_DILOCO_OPTIMIZER_SMOKE_COMMAND),
            )
        )
    elif milestone == M085R_MILESTONE:
        commands.append(
            (
                "integrated_diloco_smoke_command",
                list(M085R_INTEGRATED_DILOCO_SMOKE_COMMAND),
            )
        )
    elif milestone == M087R_MILESTONE:
        commands.append(
            (
                "parameter_fragment_smoke_command",
                list(M087R_PARAMETER_FRAGMENT_SMOKE_COMMAND),
            )
        )
    elif milestone == M089R_MILESTONE:
        commands.append(
            (
                "bounded_diloco_experiment_command",
                list(M089R_BOUNDED_DILOCO_EXPERIMENT_COMMAND),
            )
        )
    elif milestone == M093R_MILESTONE:
        commands.append(
            (
                "tiny_real_training_smoke_command",
                list(M093R_TINY_REAL_TRAINING_SMOKE_COMMAND),
            )
        )
    else:
        commands.extend(
            [
                (
                    "decodilo_profile_summary_check",
                    [
                        "env",
                        f"PYTHONPATH={runtime_path}",
                        "python3",
                        "-m",
                        "decodilo.cli",
                        "dev",
                        "test-profile-summary",
                    ],
                ),
                (
                    "decodilo_ci_profile_report_smoke",
                    [
                        "env",
                        f"PYTHONPATH={runtime_path}",
                        "python3",
                        "-m",
                        "decodilo.cli",
                        "dev",
                        "ci-profile-report",
                        "--out",
                        "/tmp/decodilo-remote-ci-profile-report.json",
                    ],
                ),
            ]
        )
    entries = [
        LambdaRemoteVerticalSliceCommandEntry(
            stage=stage,
            exact_command=render_lambda_remote_vertical_slice_argv(argv),
            argv_tokens=argv,
            timeout_seconds=60 if stage == "dependency_install_or_path_setup" else 30,
            failure_stage_if_nonzero=stage,
        )
        for stage, argv in commands
    ]
    return LambdaRemoteVerticalSliceCommandManifest(
        milestone=milestone,
        max_remote_commands=len(entries),
        command_entries=entries,
        dependency_strategy="local_wheelhouse_no_index"
        if use_wheelhouse_install
        else "local_site_packages_pythonpath",
        no_internet_install=True,
        no_downloads=True,
        no_training=True,
    )


def _m067r3_final_counts() -> tuple[int | None, int | None]:
    for path in (
        Path("/tmp/decodilo-lambda-post-m067r3-summary.json"),
        Path("/tmp/decodilo-lambda-post-m067r3-summary-3.json"),
    ):
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload.get("instance_count"), payload.get("unmanaged_count")
    return None, None


def _missing_module_from_stderr(stderr: str) -> str | None:
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", stderr)
    return match.group(1) if match else None


def _read_pyproject_dependencies(path: str | Path) -> tuple[list[str], list[str]]:
    text = Path(path).read_text(encoding="utf-8")
    if tomllib is not None:
        payload = tomllib.loads(text)
        project = payload.get("project", {})
        runtime = list(project.get("dependencies", []) or [])
        optional = project.get("optional-dependencies", {}) or {}
        dev = list(optional.get("dev", []) or [])
        return runtime, dev
    runtime = re.findall(r'"([^"]+)"', text.split("[project.optional-dependencies]")[0])
    dev_section = text.split("dev = [", 1)[1].split("]", 1)[0] if "dev = [" in text else ""
    dev = re.findall(r'"([^"]+)"', dev_section)
    return runtime, dev


def _runtime_package_closure(items: list[str]) -> list[str]:
    packages = set(items)
    for package in list(items):
        try:
            dist = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            continue
        for requirement in dist.requires or []:
            name = re.split(r"[<>=!~;\\[ ]", requirement, maxsplit=1)[0].strip()
            if name:
                packages.add(name.replace("_", "-"))
    return sorted(packages)


def _package_paths(package: str) -> list[Path]:
    paths: list[Path] = []
    spec = importlib.util.find_spec(package.replace("-", "_"))
    if spec is not None and spec.origin:
        origin = Path(spec.origin)
        paths.append(origin.parent if origin.name == "__init__.py" else origin)
    try:
        dist = importlib.metadata.distribution(package)
        if dist.files:
            root = Path(dist.locate_file(""))
            dist_info = next(
                (root / file for file in dist.files if str(file).endswith(".dist-info/METADATA")),
                None,
            )
            if dist_info is not None:
                paths.append(dist_info.parent)
    except importlib.metadata.PackageNotFoundError:
        pass
    return sorted({path for path in paths if path.exists()})


def _incompatibility_notes(paths: list[Path]) -> list[str]:
    notes: list[str] = []
    system = platform.system().lower()
    for root in paths:
        for path in ([root] if root.is_file() else root.rglob("*")):
            suffixes = "".join(path.suffixes)
            if ".so" in suffixes or ".dylib" in suffixes or ".pyd" in suffixes:
                notes.append(
                    "compiled_extension_not_compatible_with_remote_linux_python_"
                    f"{TARGET_REMOTE_PYTHON}:{path.name}"
                )
    if system != "linux":
        notes.append(f"local_platform_{system}_differs_from_remote_linux")
    return sorted(set(notes))


def _dependency_member_forbidden(name: str) -> bool:
    parts = set(Path(name).parts)
    if parts & {"__pycache__", ".git", ".pytest_cache", ".ruff_cache"}:
        return True
    basename = Path(name).name
    return basename == ".env" or basename.endswith((".pem", ".key", ".ppk", ".pyc"))


def _wheel_name_matches(name: str, package: str) -> bool:
    normalized = Path(name).name.replace("_", "-").lower()
    return normalized.startswith(f"{package.lower()}-") and normalized.endswith(".whl")


def _secret_value_hits(path: Path) -> list[str]:
    if path.suffix in {".so", ".dylib", ".pyd"}:
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    hits = []
    patterns = {
        "private_key_material": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "authorization_bearer_value": r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]{16,}",
        "api_key_value": r"api[_-]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]{16,}",
        "password_value": r"password\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            hits.append(name)
    return hits


def _path_total_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lambda_m067r_dependency_failure_record(
    path: str | Path,
) -> LambdaM067RDependencyFailureRecord:
    return LambdaM067RDependencyFailureRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_runtime_dependency_inventory(
    path: str | Path,
) -> LambdaRuntimeDependencyInventory:
    return LambdaRuntimeDependencyInventory.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_dependency_bundle_manifest(path: str | Path) -> LambdaDependencyBundleManifest:
    return LambdaDependencyBundleManifest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_dependency_bundle_validation(
    path: str | Path,
) -> LambdaDependencyBundleValidation:
    return LambdaDependencyBundleValidation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m067r_dependency_failure_record(
    path: str | Path,
    report: LambdaM067RDependencyFailureRecord,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_runtime_dependency_inventory(
    path: str | Path,
    report: LambdaRuntimeDependencyInventory,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_dependency_bundle_manifest(
    path: str | Path,
    report: LambdaDependencyBundleManifest,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_dependency_bundle_validation(
    path: str | Path,
    report: LambdaDependencyBundleValidation,
) -> None:
    _write_json(path, report.to_json())


def _write_json(path: str | Path, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
