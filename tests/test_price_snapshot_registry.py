import json

import pytest

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.registry import (
    import_html_snapshot,
    import_json_snapshot,
    query_snapshot_price,
)
from decodilo.pricing.snapshots import write_price_snapshot


def test_import_json_snapshot_marks_sample_and_queries_record(tmp_path) -> None:
    out = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=out,
        is_sample_data=True,
    )
    record = query_snapshot_price(
        snapshot,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
    )

    assert out.exists()
    assert snapshot.is_sample_data is True
    assert snapshot.source_type == "fixture"
    assert snapshot.source_sha256
    assert record.record_id
    assert record.price_per_gpu_hour == 2.49


def test_import_html_snapshot_produces_equivalent_prices(tmp_path) -> None:
    out = tmp_path / "snapshot.json"
    snapshot = import_html_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_pricing_snapshot.html",
        output_path=out,
        is_sample_data=True,
    )

    assert [record.gpu_type for record in snapshot.records] == ["H100 SXM", "A100 SXM"]


def test_ambiguous_snapshot_price_query_fails_closed(tmp_path) -> None:
    out = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=out,
        is_sample_data=False,
    )
    duplicate = snapshot.records[0].model_copy(update={"record_id": "duplicate-h100"})
    ambiguous = snapshot.model_copy(update={"records": [snapshot.records[0], duplicate]})
    write_price_snapshot(out, ambiguous)

    with pytest.raises(PricingAmbiguityError, match="ambiguous"):
        query_snapshot_price(ambiguous, gpu_type="H100 SXM", gpus_per_instance=8)

    selected = query_snapshot_price(
        ambiguous,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        allow_ambiguous_price=True,
    )
    assert selected.record_id == "duplicate-h100"
    assert json.loads(out.read_text(encoding="utf-8"))["snapshot_id"] == ambiguous.snapshot_id
