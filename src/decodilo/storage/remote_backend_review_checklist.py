"""Human review checklist for future remote backend proposals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChecklistCategory = Literal[
    "requirements",
    "conformance",
    "security",
    "credentials",
    "encryption",
    "integrity",
    "lifecycle",
    "replay_restore",
    "cost",
    "bandwidth",
    "observability",
    "rollback",
    "sdk_guard",
    "legal_compliance",
    "human_approval",
]


class RemoteBackendReviewItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    category: ChecklistCategory
    description: str
    acknowledged: bool = False
    required: bool = True
    human_placeholder: bool = False


class RemoteBackendReviewChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    checklist_schema_version: int = 1
    proposal_ref: str | None = None
    items: list[RemoteBackendReviewItem]
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False


class RemoteBackendReviewChecklistReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    incomplete_items: list[str] = Field(default_factory=list)
    human_placeholders_remaining: list[str] = Field(default_factory=list)
    checklist: RemoteBackendReviewChecklist

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_review_checklist(
    *,
    proposal_ref: str | None = None,
    acknowledge_technical: bool = False,
    acknowledge_human_placeholders: bool = False,
) -> RemoteBackendReviewChecklist:
    items = [
        _item("requirements_reviewed", "requirements", acknowledge_technical),
        _item("conformance_reviewed", "conformance", acknowledge_technical),
        _item("security_reviewed", "security", acknowledge_technical),
        _item("credentials_reviewed", "credentials", acknowledge_technical),
        _item("encryption_reviewed", "encryption", acknowledge_technical),
        _item("integrity_reviewed", "integrity", acknowledge_technical),
        _item("lifecycle_reviewed", "lifecycle", acknowledge_technical),
        _item("replay_restore_reviewed", "replay_restore", acknowledge_technical),
        _item("cost_reviewed", "cost", acknowledge_technical),
        _item("bandwidth_reviewed", "bandwidth", acknowledge_technical),
        _item("observability_reviewed", "observability", acknowledge_technical),
        _item("rollback_reviewed", "rollback", acknowledge_technical),
        _item("sdk_guard_reviewed", "sdk_guard", acknowledge_technical),
        _item(
            "legal_compliance_placeholder",
            "legal_compliance",
            acknowledge_human_placeholders,
            human=True,
        ),
        _item(
            "human_approval_placeholder",
            "human_approval",
            acknowledge_human_placeholders,
            human=True,
        ),
    ]
    return RemoteBackendReviewChecklist(proposal_ref=proposal_ref, items=items)


def evaluate_remote_backend_review_checklist(
    checklist: RemoteBackendReviewChecklist,
) -> RemoteBackendReviewChecklistReport:
    incomplete = [
        item.item_id for item in checklist.items if item.required and not item.acknowledged
    ]
    human_remaining = [
        item.item_id
        for item in checklist.items
        if item.human_placeholder and not item.acknowledged
    ]
    return RemoteBackendReviewChecklistReport(
        passed=not incomplete,
        incomplete_items=incomplete,
        human_placeholders_remaining=human_remaining,
        checklist=checklist,
    )


def load_remote_backend_review_checklist_report(
    path: str | Path,
) -> RemoteBackendReviewChecklistReport:
    return RemoteBackendReviewChecklistReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_review_checklist_report(
    path: str | Path,
    report: RemoteBackendReviewChecklistReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _item(
    item_id: str,
    category: ChecklistCategory,
    acknowledged: bool,
    *,
    human: bool = False,
) -> RemoteBackendReviewItem:
    return RemoteBackendReviewItem(
        item_id=item_id,
        category=category,
        description=item_id.replace("_", " "),
        acknowledged=acknowledged,
        human_placeholder=human,
    )
