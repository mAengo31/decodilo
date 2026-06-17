import json

from decodilo.pricing.lambda_prices import (
    get_price,
    load_lambda_prices_from_json,
    parse_lambda_pricing_html,
)


def test_price_parser_extracts_expected_prices() -> None:
    fixture = "tests/fixtures/lambda_pricing_snapshot.html"
    with open("tests/fixtures/lambda_prices_expected.json", encoding="utf-8") as handle:
        expected = json.load(handle)

    prices = parse_lambda_pricing_html(fixture, source_url=fixture)

    assert [price.model_dump(mode="json") for price in prices] == expected["prices"]


def test_static_json_loader_and_query_api() -> None:
    prices = load_lambda_prices_from_json("tests/fixtures/lambda_prices_expected.json")

    h100 = get_price(
        prices,
        provider="lambda",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
    )

    assert h100.instance_type == "gpu_8x_h100_sxm"
    assert h100.price_per_instance_hour == 19.92
