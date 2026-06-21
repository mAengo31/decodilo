from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.evidence_freshness import (
    LambdaEvidenceFreshnessPolicy,
    evaluate_lambda_evidence_freshness,
)


def test_fresh_evidence_passes(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)

    report = evaluate_lambda_evidence_freshness(
        m019c_discovery=paths["discovery"],
        price_snapshot=paths["m020"],
        m025_review=paths["review"],
        semantic_audit=paths["semantic"],
    )

    assert report.freshness_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_stale_discovery_blocks_when_policy_says_so(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    old = datetime.now(UTC) - timedelta(hours=48)
    os.utime(paths["discovery"], (old.timestamp(), old.timestamp()))

    report = evaluate_lambda_evidence_freshness(
        m019c_discovery=paths["discovery"],
        price_snapshot=paths["m020"],
        m025_review=paths["review"],
        semantic_audit=paths["semantic"],
    )

    assert "m019c_discovery" in report.stale_items
    assert report.freshness_passed is False


def test_stale_evidence_can_warn_without_blocking_for_review_only(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    old = datetime.now(UTC) - timedelta(hours=48)
    os.utime(paths["discovery"], (old.timestamp(), old.timestamp()))

    report = evaluate_lambda_evidence_freshness(
        m019c_discovery=paths["discovery"],
        price_snapshot=paths["m020"],
        m025_review=paths["review"],
        semantic_audit=paths["semantic"],
        policy=LambdaEvidenceFreshnessPolicy(stale_blocks_m027_authorization=False),
    )

    assert "m019c_discovery" in report.stale_items
    assert report.freshness_passed is True


def test_missing_required_timestamp_source_blocks(tmp_path):
    report = evaluate_lambda_evidence_freshness(
        m019c_discovery=tmp_path / "missing.json",
        price_snapshot=tmp_path / "missing-price.json",
        m025_review=tmp_path / "missing-review.json",
    )

    assert report.freshness_passed is False
    assert set(report.missing_items) >= {"m019c_discovery", "price_snapshot", "m025_review"}
