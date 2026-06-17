"""Recovery manifest chain validation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.checksums import sha256_file
from decodilo.syncer.recovery_manifest import RecoveryManifest, load_recovery_manifest


class RecoveryManifestChainReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    latest_manifest_path: str | None
    manifests_checked: int
    chain_hashes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def discover_latest_recovery_manifest(workdir: str | Path) -> Path | None:
    root = Path(workdir)
    latest = root / "recovery_manifest.json"
    if latest.exists():
        return latest
    manifests = sorted((root / "recovery_manifests").glob("*.json"))
    return manifests[-1] if manifests else None


def validate_recovery_manifest_chain(workdir: str | Path) -> RecoveryManifestChainReport:
    root = Path(workdir)
    latest_path = discover_latest_recovery_manifest(root)
    if latest_path is None:
        return RecoveryManifestChainReport(
            passed=False,
            latest_manifest_path=None,
            manifests_checked=0,
            errors=["missing recovery manifest"],
        )
    errors: list[str] = []
    checked = 0
    chain_hashes: list[str] = []
    versioned_paths = sorted((root / "recovery_manifests").glob("*.json"))
    by_hash: dict[str, tuple[Path, RecoveryManifest]] = {}
    for path in versioned_paths + [latest_path]:
        try:
            manifest = load_recovery_manifest(path)
        except Exception as exc:  # noqa: BLE001 - chain report includes failure details
            errors.append(f"invalid recovery manifest {path}: {exc}")
            continue
        by_hash[manifest.manifest_hash] = (path, manifest)
    pointer = root / "recovery_manifest.json"
    if pointer.exists() and latest_path != pointer:
        try:
            pointer_manifest = load_recovery_manifest(pointer)
            latest_manifest = load_recovery_manifest(latest_path)
            if pointer_manifest.manifest_hash != latest_manifest.manifest_hash:
                errors.append("recovery_manifest.json does not point to latest manifest")
            elif sha256_file(pointer) != sha256_file(latest_path):
                errors.append("recovery_manifest.json bytes differ from latest manifest")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid recovery manifest pointer: {exc}")
    if pointer.exists() and versioned_paths:
        try:
            pointer_manifest = load_recovery_manifest(pointer)
            versions = [
                manifest.global_version
                for _, manifest in by_hash.values()
                if manifest.global_version is not None
            ]
            if (
                pointer_manifest.global_version is not None
                and versions
                and pointer_manifest.global_version < max(versions)
            ):
                errors.append("recovery manifest pointer global_version regression")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid recovery manifest pointer: {exc}")

    try:
        current = load_recovery_manifest(latest_path)
    except Exception as exc:  # noqa: BLE001
        return RecoveryManifestChainReport(
            passed=False,
            latest_manifest_path=str(latest_path),
            manifests_checked=0,
            errors=[f"invalid latest recovery manifest: {exc}"],
        )
    previous_version = current.global_version
    seen: set[str] = set()
    while True:
        checked += 1
        chain_hashes.append(current.manifest_hash)
        if current.manifest_hash in seen:
            errors.append("recovery manifest chain contains a cycle")
            break
        seen.add(current.manifest_hash)
        previous_hash = current.previous_recovery_manifest_hash
        if previous_hash is None:
            break
        previous = by_hash.get(previous_hash)
        if previous is None:
            errors.append(f"missing previous recovery manifest {previous_hash}")
            break
        _, previous_manifest = previous
        if current.run_id != previous_manifest.run_id:
            errors.append("recovery manifest chain run_id mismatch")
        if (
            previous_version is not None
            and previous_manifest.global_version is not None
            and previous_manifest.global_version > previous_version
        ):
            errors.append("recovery manifest chain global_version regression")
        previous_version = previous_manifest.global_version
        current = previous_manifest
    return RecoveryManifestChainReport(
        passed=not errors,
        latest_manifest_path=str(latest_path),
        manifests_checked=checked,
        chain_hashes=chain_hashes,
        errors=errors,
    )
