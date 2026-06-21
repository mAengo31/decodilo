from __future__ import annotations

import json

from lambda_m051_helpers import write_m051_inputs


def test_cloud_still_disabled_m051(tmp_path):
    paths = write_m051_inputs(tmp_path)
    artifacts = [
        paths["metadata_plan"],
        paths["execution_gate"],
        paths["audit_m051"],
        paths["authorization"],
        paths["runbook"],
        paths["m050"],
    ]

    for path in artifacts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["launch_ready"] is False
        assert payload["launch_allowed"] is False
        assert payload["billable_action_performed"] is False
        assert payload["real_mutation_enabled"] is False
