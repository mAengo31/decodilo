from __future__ import annotations

import json

from lambda_m051_helpers import write_m051_inputs


def test_cloud_still_disabled_m051a(tmp_path):
    paths = write_m051_inputs(tmp_path)
    artifacts = [
        paths["operator_confirmation_m051"],
        paths["one_shot_arming_m051"],
        paths["command_binding_m051"],
        paths["artifact_binding_m051"],
        paths["reviewer_bridge_m051"],
        paths["arming_gate_m051"],
        paths["arming_command_preview_m051"],
    ]

    for path in artifacts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["launch_ready"] is False
        assert payload["launch_allowed"] is False
        assert payload["billable_action_performed"] is False
        assert payload["real_mutation_enabled"] is False

    arming = json.loads(paths["one_shot_arming_m051"].read_text(encoding="utf-8"))
    bridge = json.loads(paths["reviewer_bridge_m051"].read_text(encoding="utf-8"))
    assert arming["one_shot_request_send_permitted"] is False
    assert bridge["one_shot_request_send_permitted"] is True
