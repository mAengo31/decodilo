from __future__ import annotations

import json

from lambda_m052_helpers import write_m052_inputs


def test_cloud_still_disabled_m052(tmp_path):
    paths = write_m052_inputs(tmp_path)
    artifacts = [
        paths["success"],
        paths["reconciliation"],
        paths["evidence"],
        paths["closeout"],
        paths["attestation"],
        paths["comparison"],
        paths["strategy"],
        paths["decision"],
        paths["m052"],
    ]

    for path in artifacts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["launch_ready"] is False
        assert payload["launch_allowed"] is False
        assert payload["billable_action_performed"] is False
        assert payload["real_mutation_enabled"] is False
