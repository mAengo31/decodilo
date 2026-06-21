from __future__ import annotations

import json

from lambda_m047_helpers import write_m047_inputs


def test_cloud_still_disabled_m047(tmp_path):
    paths = write_m047_inputs(tmp_path)
    artifacts = [
        paths["success"],
        paths["reconciliation"],
        paths["evidence"],
        paths["closeout"],
        paths["parsed_instance_types"],
        paths["region_selection"],
        paths["alias"],
        paths["price_join"],
        paths["strategy"],
        paths["m047"],
    ]

    for path in artifacts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["launch_ready"] is False
        assert payload["launch_allowed"] is False
        assert payload["billable_action_performed"] is False
        assert payload["real_mutation_enabled"] is False
