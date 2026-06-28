"""Offline/future selector for Decodilo remote vertical-slice candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_proven_candidate_policy import (
    load_lambda_ssh_proven_candidate_policy,
)
from decodilo.lambda_cloud.ssh_readiness_history import (
    load_lambda_ssh_readiness_history,
)

LambdaRemoteVSliceCandidateSelectionStatus = Literal[
    "requires_fresh_readonly_discovery",
    "selected_ssh_proven_candidate",
    "known_ssh_ready_candidate_not_live",
    "require_operator_approval_for_new_candidate_exploration",
    "no_candidate",
]


class LambdaRemoteVSliceCandidateSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selection_status: LambdaRemoteVSliceCandidateSelectionStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    preferred_known_good_candidate_region: dict[str, str] | None = None
    excluded_candidate_regions: list[dict[str, str | int]] = Field(default_factory=list)
    live_candidate_regions_seen: list[dict[str, str]] = Field(default_factory=list)
    operator_approval_required_for_new_candidate: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteVSliceCandidateSelection:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("remote vertical-slice selector cannot enable launch")
        if self.selection_status == "selected_ssh_proven_candidate" and (
            not self.selected_candidate or not self.selected_region
        ):
            raise ValueError("selected SSH-proven candidate requires candidate and region")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vslice_candidate_selection_from_paths(
    *,
    ssh_readiness_history: str | Path,
    ssh_proven_policy: str | Path,
    price_snapshot: str | Path | None = None,
    discovery_report: str | Path | None = None,
) -> LambdaRemoteVSliceCandidateSelection:
    del price_snapshot
    history = load_lambda_ssh_readiness_history(ssh_readiness_history)
    policy = load_lambda_ssh_proven_candidate_policy(ssh_proven_policy)
    preferred = policy.preferred_known_good_candidate_region
    if discovery_report is None:
        return LambdaRemoteVSliceCandidateSelection(
            selection_status="requires_fresh_readonly_discovery",
            preferred_known_good_candidate_region=preferred,
            excluded_candidate_regions=policy.excluded_candidate_regions,
            blockers=["fresh_readonly_discovery_required"],
            warnings=[
                "M067S did not call live Lambda; future retry requires fresh read-only discovery",
            ],
        )

    discovery = json.loads(Path(discovery_report).read_text(encoding="utf-8"))
    live_pairs = _extract_live_candidate_regions(discovery)
    excluded_pairs = {
        (str(item["selected_candidate"]), str(item["selected_region"]))
        for item in policy.excluded_candidate_regions
    }
    proven_pairs = {
        (str(item["selected_candidate"]), str(item["selected_region"]))
        for item in policy.ssh_proven_candidate_regions
    }
    live_pair_set = {
        (item["selected_candidate"], item["selected_region"]) for item in live_pairs
    }
    selected: tuple[str, str] | None = None
    if preferred:
        candidate = preferred["selected_candidate"]
        region = preferred["selected_region"]
        if (candidate, region) in live_pair_set and (candidate, region) not in excluded_pairs:
            selected = (candidate, region)
    if selected is None:
        for candidate, region in sorted(proven_pairs):
            if (candidate, region) in live_pair_set and (candidate, region) not in excluded_pairs:
                selected = (candidate, region)
                break
    if selected is not None:
        return LambdaRemoteVSliceCandidateSelection(
            selection_status="selected_ssh_proven_candidate",
            selected_candidate=selected[0],
            selected_region=selected[1],
            preferred_known_good_candidate_region=preferred,
            excluded_candidate_regions=policy.excluded_candidate_regions,
            live_candidate_regions_seen=live_pairs,
            warnings=[
                "Cost is secondary after SSH readiness for Decodilo vertical slices",
            ],
        )
    live_unexcluded = [
        pair
        for pair in live_pairs
        if (pair["selected_candidate"], pair["selected_region"]) not in excluded_pairs
    ]
    if proven_pairs:
        return LambdaRemoteVSliceCandidateSelection(
            selection_status="known_ssh_ready_candidate_not_live",
            preferred_known_good_candidate_region=preferred,
            excluded_candidate_regions=policy.excluded_candidate_regions,
            live_candidate_regions_seen=live_pairs,
            blockers=["known_ssh_ready_candidate_not_live"],
            warnings=[
                "Do not silently substitute an unproven candidate for a Decodilo vertical slice",
            ],
        )
    if live_unexcluded:
        return LambdaRemoteVSliceCandidateSelection(
            selection_status="require_operator_approval_for_new_candidate_exploration",
            preferred_known_good_candidate_region=history.preferred_known_good_candidate_region,
            excluded_candidate_regions=policy.excluded_candidate_regions,
            live_candidate_regions_seen=live_pairs,
            operator_approval_required_for_new_candidate=True,
            blockers=["operator_approval_required_for_new_candidate_exploration"],
        )
    return LambdaRemoteVSliceCandidateSelection(
        selection_status="no_candidate",
        preferred_known_good_candidate_region=preferred,
        excluded_candidate_regions=policy.excluded_candidate_regions,
        live_candidate_regions_seen=live_pairs,
        blockers=["no_candidate_region_available"],
    )


def _extract_live_candidate_regions(discovery: dict[str, Any]) -> list[dict[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for item in discovery.get("instance_types", []) or []:
        candidate = item.get("name") or item.get("instance_type_name")
        if not candidate:
            continue
        for region in _regions_from_item(item):
            pairs.add((str(candidate), region))
    return [
        {"selected_candidate": candidate, "selected_region": region}
        for candidate, region in sorted(pairs)
    ]


def _regions_from_item(item: dict[str, Any]) -> list[str]:
    direct = item.get("region") or item.get("region_name")
    if isinstance(direct, str) and direct:
        return [direct]
    regions = item.get("regions") or []
    result: list[str] = []
    if isinstance(regions, list):
        for region in regions:
            if isinstance(region, str) and region:
                result.append(region)
            elif isinstance(region, dict):
                value = region.get("name") or region.get("region_name")
                if isinstance(value, str) and value:
                    result.append(value)
    return result


def load_lambda_remote_vslice_candidate_selection(
    path: str | Path,
) -> LambdaRemoteVSliceCandidateSelection:
    return LambdaRemoteVSliceCandidateSelection.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_candidate_selection(
    path: str | Path,
    report: LambdaRemoteVSliceCandidateSelection,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
