import json
import subprocess
import sys

import pytest

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.budget import BudgetGuard
from decodilo.pricing.lambda_prices import get_price
from decodilo.pricing.models import PriceProfile


def _price(instance_type: str, gpu_price: float = 2.49) -> PriceProfile:
    return PriceProfile(
        provider="lambda",
        instance_type=instance_type,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        gpu_memory_gb=80,
        price_per_gpu_hour=gpu_price,
        price_per_instance_hour=8 * gpu_price,
        region="test",
        source_url="fixture",
        source_timestamp="2026-06-16T00:00:00Z",
    )


def test_price_lookup_fails_closed_on_no_match() -> None:
    with pytest.raises(PricingAmbiguityError):
        get_price([_price("shape")], gpu_type="A100 SXM", gpus_per_instance=8)


def test_price_lookup_fails_closed_on_ambiguous_match() -> None:
    prices = [_price("shape-a"), _price("shape-b")]

    with pytest.raises(PricingAmbiguityError):
        get_price(prices, gpu_type="H100 SXM", gpus_per_instance=8)


def test_price_lookup_requires_explicit_ambiguous_override() -> None:
    prices = [_price("shape-b"), _price("shape-a")]

    selected = get_price(
        prices,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        allow_ambiguous_price=True,
    )

    assert selected.instance_type == "shape-a"


def test_budget_guard_fails_closed_on_max_budget_and_adjusted_credit_limit() -> None:
    guard = BudgetGuard(starting_credits=100.0, safety_buffer_pct=0.15)

    over_max = guard.check_run(estimated_run_cost=90.0, max_run_budget=80.0)
    assert not over_max.allowed
    assert over_max.reason == "planned run exceeds max_run_budget"

    over_credits = guard.check_run(estimated_run_cost=90.0, max_run_budget=100.0)
    assert not over_credits.allowed
    assert over_credits.reason == "projected remaining credits would be negative"
    assert over_credits.safety_buffer_adjusted_cost == 103.5


def test_budget_cli_prints_transparent_arithmetic_for_fixture() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "budget",
            "estimate",
            "--credits",
            "7500",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--instances",
            "1",
            "--hours",
            "10",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["selected_provider"] == "lambda"
    assert payload["selected_gpu_type"] == "H100 SXM"
    assert payload["selected_instance_shape"] == "gpu_8x_h100_sxm"
    assert payload["price_per_gpu_hour"] == 2.49
    assert payload["price_per_instance_hour"] == 19.92
    assert payload["instances"] == 1
    assert payload["total_gpus"] == 8
    assert payload["planned_hours"] == 10.0
    assert payload["base_estimated_cost"] == 199.20000000000002
    assert payload["safety_buffer_pct"] == 0.15
    assert payload["safety_buffer_adjusted_cost"] == 229.08
    assert payload["projected_remaining_credits"] == 7270.92
    assert payload["price_source_url"] == "packaged-offline-sample"
    assert payload["tax_included"] is False


def test_budget_cli_arithmetic_reflects_selected_price_file(tmp_path) -> None:
    price_json = tmp_path / "prices.json"
    price_json.write_text(
        json.dumps({"prices": [_price("h100-expensive", gpu_price=3.99).model_dump(mode="json")]}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "budget",
            "estimate",
            "--credits",
            "7500",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--instances",
            "1",
            "--hours",
            "10",
            "--price-json",
            str(price_json),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["price_per_gpu_hour"] == 3.99
    assert payload["price_per_instance_hour"] == 31.92
    assert payload["base_estimated_cost"] == 319.20000000000005

