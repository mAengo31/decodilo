"""Evidence package models for future remote backend implementation review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    path: str
    sha256: str | None
    present: bool
    required: bool = True
    errors: list[str] = Field(default_factory=list)


class RemoteBackendEvidenceManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    items: list[RemoteBackendEvidenceItem]
    evidence_completeness_score: float
    missing_required_items: list[str] = Field(default_factory=list)
    hash_errors: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RemoteBackendEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_schema_version: int = 1
    scenario_id: str = "remote-backend-evidence"
    manifest: RemoteBackendEvidenceManifest
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_evidence_package(
    *,
    evidence_paths: dict[str, str | Path | None],
    scenario_id: str = "remote-backend-evidence",
) -> RemoteBackendEvidencePackage:
    items: list[RemoteBackendEvidenceItem] = []
    missing: list[str] = []
    blockers: list[str] = []
    for item_id, raw_path in evidence_paths.items():
        if raw_path is None:
            missing.append(item_id)
            blockers.append(f"missing required evidence item: {item_id}")
            items.append(
                RemoteBackendEvidenceItem(
                    item_id=item_id,
                    path="",
                    sha256=None,
                    present=False,
                    errors=["path not provided"],
                )
            )
            continue
        path = Path(raw_path)
        if not path.exists():
            missing.append(item_id)
            blockers.append(f"missing required evidence item: {item_id}")
            items.append(
                RemoteBackendEvidenceItem(
                    item_id=item_id,
                    path=str(path),
                    sha256=None,
                    present=False,
                    errors=["file does not exist"],
                )
            )
            continue
        items.append(
            RemoteBackendEvidenceItem(
                item_id=item_id,
                path=str(path),
                sha256=_sha256_file(path),
                present=True,
            )
        )
    present_required = sum(1 for item in items if item.required and item.present)
    required_total = sum(1 for item in items if item.required)
    completeness = present_required / required_total if required_total else 1.0
    manifest = RemoteBackendEvidenceManifest(
        items=items,
        evidence_completeness_score=completeness,
        missing_required_items=missing,
        blockers=blockers,
        warnings=[
            "evidence package is review input only; it does not enable remote backend",
        ],
    )
    return RemoteBackendEvidencePackage(scenario_id=scenario_id, manifest=manifest)


def validate_remote_backend_evidence_package(
    package: RemoteBackendEvidencePackage,
) -> RemoteBackendEvidenceManifest:
    hash_errors: list[str] = []
    items: list[RemoteBackendEvidenceItem] = []
    missing: list[str] = []
    blockers = list(package.manifest.blockers)
    for item in package.manifest.items:
        path = Path(item.path) if item.path else None
        if path is None or not path.exists():
            missing.append(item.item_id)
            blockers.append(f"missing required evidence item: {item.item_id}")
            items.append(item.model_copy(update={"present": False, "errors": ["file missing"]}))
            continue
        actual = _sha256_file(path)
        errors = list(item.errors)
        if item.sha256 != actual:
            hash_errors.append(item.item_id)
            errors.append("sha256 mismatch")
        items.append(
            item.model_copy(
                update={"present": True, "sha256": item.sha256, "errors": errors}
            )
        )
    present_required = sum(1 for item in items if item.required and item.present)
    required_total = sum(1 for item in items if item.required)
    completeness = present_required / required_total if required_total else 1.0
    return RemoteBackendEvidenceManifest(
        items=items,
        evidence_completeness_score=completeness,
        missing_required_items=missing,
        hash_errors=hash_errors,
        blockers=blockers + [f"hash mismatch: {item}" for item in hash_errors],
        warnings=package.manifest.warnings,
    )


def load_remote_backend_evidence_package(path: str | Path) -> RemoteBackendEvidencePackage:
    return RemoteBackendEvidencePackage.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_evidence_package(
    path: str | Path,
    package: RemoteBackendEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
