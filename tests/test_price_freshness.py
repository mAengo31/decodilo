from datetime import UTC, datetime

import pytest

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.freshness import require_usable_snapshot, snapshot_age_days
from decodilo.pricing.registry import import_json_snapshot


def test_snapshot_freshness_rejects_stale_by_default(tmp_path) -> None:
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=tmp_path / "snapshot.json",
        is_sample_data=False,
    ).model_copy(update={"captured_at_utc": "2026-06-01T00:00:00Z"})

    now = datetime(2026, 6, 16, tzinfo=UTC)
    assert snapshot_age_days(snapshot, now=now) == 15.0
    with pytest.raises(PricingAmbiguityError, match="stale"):
        require_usable_snapshot(snapshot, now=now)
    require_usable_snapshot(snapshot, allow_stale_prices=True, now=now)


def test_sample_snapshot_rejected_by_default(tmp_path) -> None:
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=tmp_path / "snapshot.json",
        is_sample_data=True,
    )

    with pytest.raises(PricingAmbiguityError, match="sample"):
        require_usable_snapshot(snapshot)
    require_usable_snapshot(snapshot, allow_sample_prices=True)
