"""Offline Lambda Cloud fixture data and loaders."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_LAMBDA_FIXTURES: dict[str, Any] = {
    "regions": [
        {"region_id": "us-west-1", "name": "US West 1", "available": True},
        {"region_id": "us-east-1", "name": "US East 1", "available": True},
    ],
    "instance_types": [
        {
            "instance_type_id": "gpu_8x_h100_sxm",
            "name": "8x H100 SXM",
            "gpu_type": "H100 SXM",
            "gpus": 8,
            "memory_gb": 1800,
            "vcpus": 192,
            "price_per_hour": 29.52,
            "regions": ["us-west-1"],
        },
        {
            "instance_type_id": "gpu_1x_a10",
            "name": "1x A10",
            "gpu_type": "A10",
            "gpus": 1,
            "memory_gb": 64,
            "vcpus": 24,
            "price_per_hour": 0.75,
            "regions": ["us-east-1", "us-west-1"],
        },
    ],
    "images": [
        {
            "image_id": "img-ubuntu-2204-cuda-fixture",
            "name": "ubuntu-22.04-cuda-fixture",
            "family": "ubuntu",
            "description": "Fixture image; not a live Lambda image.",
        }
    ],
    "ssh_keys": [
        {
            "key_id": "key-fixture-public-only",
            "name": "fixture-public-key",
            "public_key_fingerprint": "SHA256:fixture-only",
        }
    ],
    "filesystems": [
        {
            "filesystem_id": "fs-fixture-decodi",
            "name": "fixture-decodi",
            "region_id": "us-west-1",
            "size_gb": 1024,
            "mounted": False,
        }
    ],
    "instances": [
        {
            "instance_id": "i-fixture-managed",
            "name": "fixture-managed",
            "instance_type_id": "gpu_1x_a10",
            "region_id": "us-west-1",
            "image_id": "img-ubuntu-2204-cuda-fixture",
            "status": "active",
            "hourly_cost": 0.75,
            "tags": {"decodilo_run_id": "fixture-run"},
        },
        {
            "instance_id": "i-fixture-unmanaged",
            "name": "fixture-unmanaged",
            "instance_type_id": "gpu_1x_a10",
            "region_id": "us-west-1",
            "image_id": "img-ubuntu-2204-cuda-fixture",
            "status": "active",
            "hourly_cost": 0.75,
            "tags": {},
        },
    ],
    "quota": {
        "max_instances": 4,
        "max_gpus": 16,
        "running_instances": 2,
        "running_gpus": 2,
    },
    "usage_estimate": {
        "estimated_hourly_cost": 1.5,
        "estimated_monthly_cost": 1080.0,
        "running_instance_count": 2,
        "source": "fixture",
    },
}


def load_lambda_fixture_data(fixtures_dir: str | Path | None = None) -> dict[str, Any]:
    """Load fixture data from JSON files or return built-in offline fixtures."""

    if fixtures_dir is None:
        return deepcopy(DEFAULT_LAMBDA_FIXTURES)
    root = Path(fixtures_dir)
    if not root.exists():
        return deepcopy(DEFAULT_LAMBDA_FIXTURES)
    data = deepcopy(DEFAULT_LAMBDA_FIXTURES)
    for key in data:
        path = root / f"{key}.json"
        if path.exists():
            data[key] = json.loads(path.read_text(encoding="utf-8"))
    return data


def write_lambda_fixture_data(fixtures_dir: str | Path, data: dict[str, Any] | None = None) -> None:
    """Write fixture JSON files for tests or examples."""

    root = Path(fixtures_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = deepcopy(DEFAULT_LAMBDA_FIXTURES if data is None else data)
    for key, value in payload.items():
        (root / f"{key}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
