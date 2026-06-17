import json

import pytest

from decodilo.pricing.registry import import_json_snapshot, query_snapshot_price
from decodilo.scaling.capacity_plan import build_capacity_plan
from decodilo.scaling.cost_projection import project_cost


def _h100_record(tmp_path):
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=tmp_path / "snapshot.json",
        is_sample_data=False,
    )
    return query_snapshot_price(snapshot, gpu_type="H100 SXM", gpus_per_instance=8)


def test_capacity_plan_serializes_and_warns_on_budget(tmp_path) -> None:
    plan = build_capacity_plan(
        price_record=_h100_record(tmp_path),
        num_instances=2,
        planned_hours=10,
        parameter_count=7_000_000,
        bytes_per_parameter=2,
        num_learners=4,
        expected_tokens_per_second=100_000,
        expected_goodput=0.85,
        credit_budget=10,
    )
    payload = plan.to_dict()

    assert payload["model_bytes"] == 14_000_000
    assert "budget_exceeded" in payload["warnings"]
    assert json.loads(json.dumps(payload))["bandwidth"]["average_bandwidth_gbps"] > 0


def test_capacity_plan_rejects_invalid_inputs(tmp_path) -> None:
    with pytest.raises(ValueError):
        build_capacity_plan(
            price_record=_h100_record(tmp_path),
            num_instances=1,
            planned_hours=10,
            parameter_count=0,
            bytes_per_parameter=2,
            num_learners=4,
            expected_tokens_per_second=100_000,
            expected_goodput=0.85,
            credit_budget=7500,
        )


def test_cost_per_useful_token_increases_as_goodput_decreases() -> None:
    high = project_cost(
        price_per_instance_hour=20,
        num_instances=1,
        planned_hours=1,
        expected_goodput_ratio=1.0,
        expected_useful_tokens=1000,
    )
    low = project_cost(
        price_per_instance_hour=20,
        num_instances=1,
        planned_hours=1,
        expected_goodput_ratio=0.5,
        expected_useful_tokens=500,
    )

    assert low.expected_cost_per_useful_token > high.expected_cost_per_useful_token
