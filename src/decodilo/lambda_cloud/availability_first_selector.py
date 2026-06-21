"""Convenience wrapper for availability-first Lambda candidate selection."""

from __future__ import annotations

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    LambdaAvailabilityFirstCandidateRankerReport,
    rank_lambda_availability_first_candidates,
)
from decodilo.lambda_cloud.catalog_candidate_policy import LambdaCatalogCandidatePolicy
from decodilo.lambda_cloud.catalog_candidate_rotation import (
    LambdaCatalogCandidateRotationReport,
    build_lambda_catalog_candidate_rotation,
)
from decodilo.lambda_cloud.live_capacity_candidate_extractor import (
    LambdaLiveCapacityCandidateExtractorReport,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
)
from decodilo.pricing.snapshots import PriceSnapshot


def select_lambda_availability_first_candidate(
    *,
    candidates: LambdaLiveCapacityCandidateExtractorReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    max_budget: float = 50.0,
    approved_shapes: set[str] | None = None,
    catalog_only_risk_accepted: bool = False,
) -> LambdaAvailabilityFirstCandidateRankerReport:
    """Rank and select a future-review candidate without enabling launch."""
    return rank_lambda_availability_first_candidates(
        candidates=candidates,
        ssh_key_selection=ssh_key_selection,
        max_budget=max_budget,
        approved_shapes=approved_shapes,
        catalog_only_risk_accepted=catalog_only_risk_accepted,
    )


def select_lambda_catalog_rotation_candidate(
    *,
    price_snapshot: PriceSnapshot,
    capacity_error_shapes: set[str],
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    policy: LambdaCatalogCandidatePolicy | None = None,
) -> LambdaCatalogCandidateRotationReport:
    """Rank alternative catalog candidates after capacity rejection."""
    return build_lambda_catalog_candidate_rotation(
        price_snapshot=price_snapshot,
        capacity_error_shapes=capacity_error_shapes,
        ssh_key_selection_passed=ssh_key_selection.selection_passed,
        policy=policy,
    )
