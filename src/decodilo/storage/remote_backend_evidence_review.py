"""Hash validation for remote backend review packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendEvidenceReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    artifacts_checked: int
    missing_references: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def review_evidence_hashes(
    *,
    expected_hashes: dict[str, str],
) -> RemoteBackendEvidenceReviewReport:
    missing: list[str] = []
    mismatches: list[str] = []
    for path_text, expected in expected_hashes.items():
        path = Path(path_text)
        if not path.exists():
            missing.append(path_text)
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append(path_text)
    blockers = [
        *[f"missing reference: {path}" for path in missing],
        *[f"hash mismatch: {path}" for path in mismatches],
    ]
    return RemoteBackendEvidenceReviewReport(
        passed=not blockers,
        artifacts_checked=len(expected_hashes),
        missing_references=missing,
        hash_mismatches=mismatches,
        blockers=blockers,
        warnings=["review package is evidence only and does not enable backend"],
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
