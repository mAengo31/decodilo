"""Review package assembly for future remote backend implementation review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_evidence_review import (
    RemoteBackendEvidenceReviewReport,
    review_evidence_hashes,
)


class RemoteBackendReviewPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_schema_version: int = 1
    proposal_ref: str
    decision_record_ref: str
    risk_register_ref: str
    rollout_plan_ref: str
    sdk_guard_report_ref: str
    review_checklist_ref: str | None = None
    readiness_report_ref: str | None = None
    evidence_package_ref: str | None = None
    source_evidence_hashes: dict[str, str]
    evidence_review: RemoteBackendEvidenceReviewReport
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_review_package(
    *,
    proposal_ref: str | Path,
    decision_record_ref: str | Path,
    risk_register_ref: str | Path,
    rollout_plan_ref: str | Path,
    sdk_guard_report_ref: str | Path,
    review_checklist_ref: str | Path | None = None,
    readiness_report_ref: str | Path | None = None,
    evidence_package_ref: str | Path | None = None,
) -> RemoteBackendReviewPackage:
    required_paths = [
        proposal_ref,
        decision_record_ref,
        risk_register_ref,
        rollout_plan_ref,
        sdk_guard_report_ref,
    ]
    optional_paths = [review_checklist_ref, readiness_report_ref, evidence_package_ref]
    all_paths = [Path(path) for path in required_paths] + [
        Path(path) for path in optional_paths if path is not None
    ]
    hashes = {str(path): _sha256_file(path) for path in all_paths if path.exists()}
    missing = [str(path) for path in all_paths if not path.exists()]
    review = review_evidence_hashes(expected_hashes=hashes)
    blockers = list(review.blockers) + [
        f"missing required review artifact: {path}" for path in missing
    ]
    return RemoteBackendReviewPackage(
        proposal_ref=str(proposal_ref),
        decision_record_ref=str(decision_record_ref),
        risk_register_ref=str(risk_register_ref),
        rollout_plan_ref=str(rollout_plan_ref),
        sdk_guard_report_ref=str(sdk_guard_report_ref),
        review_checklist_ref=str(review_checklist_ref) if review_checklist_ref else None,
        readiness_report_ref=str(readiness_report_ref) if readiness_report_ref else None,
        evidence_package_ref=str(evidence_package_ref) if evidence_package_ref else None,
        source_evidence_hashes=hashes,
        evidence_review=review,
        blockers=blockers,
        warnings=["review package is review-only; backend remains disabled"],
    )


def load_remote_backend_review_package(path: str | Path) -> RemoteBackendReviewPackage:
    return RemoteBackendReviewPackage.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_review_package(
    path: str | Path,
    package: RemoteBackendReviewPackage,
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
