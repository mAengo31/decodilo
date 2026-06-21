from __future__ import annotations

import pytest

from decodilo.runtime.ci_profile_manifest import classify_test_file


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    heavy_markers = {
        "integration",
        "slow",
        "soak",
        "perf",
        "lifecycle",
        "hardware_optional",
        "torch_optional",
        "subprocess_heavy",
        "lambda_live",
        "lambda_real_mutation",
    }
    for item in items:
        inferred = classify_test_file(item.path)
        existing = {mark.name for mark in item.iter_markers()}
        for marker in sorted(inferred - existing):
            item.add_marker(getattr(pytest.mark, marker))
        updated = existing | inferred
        if "unit" not in updated and not updated & heavy_markers:
            item.add_marker(pytest.mark.unit)
