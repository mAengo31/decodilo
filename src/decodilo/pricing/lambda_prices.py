"""Offline Lambda Labs pricing sources and query helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.models import PriceProfile

_MONEY_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _parse_money(value: str) -> float:
    match = _MONEY_RE.search(value.replace(",", ""))
    if not match:
        raise ValueError(f"could not parse money value: {value!r}")
    return float(match.group(0))


def _parse_int(value: str) -> int:
    match = _MONEY_RE.search(value.replace(",", ""))
    if not match:
        raise ValueError(f"could not parse integer value: {value!r}")
    return int(float(match.group(0)))


def parse_lambda_pricing_html(
    path: str | Path,
    *,
    source_url: str = "offline-fixture",
) -> list[PriceProfile]:
    """Parse a Lambda-style pricing table from a local HTML snapshot."""

    html_path = Path(path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    timestamp = "unknown"
    meta = soup.find("meta", attrs={"name": "snapshot-timestamp"})
    if meta and meta.get("content"):
        timestamp = str(meta["content"])

    prices: list[PriceProfile] = []
    for table in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True).lower()
            for cell in table.find_all("th")
        ]
        if not headers or "gpu type" not in headers:
            continue
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if not cells:
                continue
            values = dict(zip(headers, cells, strict=False))
            gpu_type = values.get("gpu type") or values.get("gpu")
            if not gpu_type:
                continue
            gpus = _parse_int(values.get("gpus", values.get("gpus per instance", "1")))
            price_per_gpu_hour = _parse_money(
                values.get("price / gpu hour", values.get("price per gpu hour", "0"))
            )
            price_per_instance_hour = values.get("price / instance hour") or values.get(
                "price per instance hour"
            )
            if price_per_instance_hour is None:
                price_per_instance_hour = str(price_per_gpu_hour * gpus)
            prices.append(
                PriceProfile(
                    provider="lambda",
                    instance_type=values.get("instance type", values.get("instance", "unknown")),
                    gpu_type=gpu_type,
                    gpus_per_instance=gpus,
                    gpu_memory_gb=float(
                        _parse_money(values.get("gpu memory (gb)", values.get("memory gb", "1")))
                    ),
                    price_per_gpu_hour=price_per_gpu_hour,
                    price_per_instance_hour=_parse_money(price_per_instance_hour),
                    region=values.get("region") or None,
                    source_url=source_url,
                    source_timestamp=timestamp,
                    tax_included=(values.get("tax included", "false").lower() == "true"),
                    notes=values.get("notes", ""),
                )
            )
    if not prices:
        raise ValueError(f"no Lambda pricing table found in {html_path}")
    return prices


def load_lambda_prices_from_json(path: str | Path) -> list[PriceProfile]:
    """Load Lambda price profiles from a local static JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data["prices"] if isinstance(data, dict) and "prices" in data else data
    return [PriceProfile.model_validate(record) for record in records]


def load_packaged_sample_prices() -> list[PriceProfile]:
    """Load offline sample prices bundled for CLI demos and tests."""

    with resources.files("decodilo.pricing").joinpath("sample_lambda_prices.json").open(
        "r",
        encoding="utf-8",
    ) as handle:
        data: Any = json.load(handle)
    return [PriceProfile.model_validate(record) for record in data["prices"]]


def get_price(
    prices: Iterable[PriceProfile] | None = None,
    *,
    provider: str = "lambda",
    gpu_type: str | None = None,
    gpus_per_instance: int | None = None,
    instance_type: str | None = None,
    region: str | None = None,
    allow_ambiguous_price: bool = False,
) -> PriceProfile:
    """Return a unique price matching the supplied query fields.

    The default is fail-closed: no match and multiple matches both raise
    PricingAmbiguityError. ``allow_ambiguous_price=True`` is an explicit
    override that chooses a deterministic first match after sorting.
    """

    candidates = list(prices) if prices is not None else load_packaged_sample_prices()
    matches: list[PriceProfile] = []
    for price in candidates:
        if price.provider != provider:
            continue
        if gpu_type is not None and price.gpu_type != gpu_type:
            continue
        if gpus_per_instance is not None and price.gpus_per_instance != gpus_per_instance:
            continue
        if instance_type is not None and price.instance_type != instance_type:
            continue
        if region is not None and price.region != region:
            continue
        matches.append(price)

    query = (
        f"provider={provider!r}, gpu_type={gpu_type!r}, "
        f"gpus_per_instance={gpus_per_instance!r}, "
        f"instance_type={instance_type!r}, region={region!r}"
    )
    if not matches:
        raise PricingAmbiguityError(f"no price matched {query}")
    if len(matches) > 1 and not allow_ambiguous_price:
        shapes = sorted(
            f"{price.instance_type}@{price.region or 'unknown-region'}"
            for price in matches
        )
        raise PricingAmbiguityError(f"ambiguous price query {query}; matches={shapes}")
    return sorted(
        matches,
        key=lambda price: (
            price.provider,
            price.gpu_type,
            price.gpus_per_instance,
            price.instance_type,
            price.region or "",
            price.price_per_instance_hour,
            price.source_timestamp,
        ),
    )[0]
