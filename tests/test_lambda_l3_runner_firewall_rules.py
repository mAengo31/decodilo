from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner():
    path = Path(__file__).resolve().parents[1] / "tools" / "lambda_l3_runner.py"
    spec = importlib.util.spec_from_file_location("lambda_l3_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lambda_l3_runner"] = module
    spec.loader.exec_module(module)
    return module


def test_temporary_firewall_rules_preserve_existing_rules_and_scope_l3_port() -> None:
    runner = _load_runner()
    original = [
        {
            "protocol": "tcp",
            "port_range": [22, 22],
            "source_network": "0.0.0.0/0",
            "description": "Allow SSH connections from any IP",
        },
        {
            "protocol": "icmp",
            "source_network": "0.0.0.0/0",
            "description": "Allow Ping from any IP",
        },
    ]

    rules = runner._temporary_firewall_rules(
        original,
        port=28080,
        learner_ips=["203.0.113.10", "203.0.113.11"],
    )

    assert original[0] in rules
    assert original[1] in rules
    l3_rules = [rule for rule in rules if rule.get("port_range") == [28080, 28080]]
    assert l3_rules == [
        {
            "protocol": "tcp",
            "port_range": [28080, 28080],
            "source_network": "203.0.113.10/32",
            "description": "Temporary Decodilo L3 learner-0 direct TCP syncer access",
        },
        {
            "protocol": "tcp",
            "port_range": [28080, 28080],
            "source_network": "203.0.113.11/32",
            "description": "Temporary Decodilo L3 learner-1 direct TCP syncer access",
        },
    ]


def test_temporary_firewall_rules_are_idempotent() -> None:
    runner = _load_runner()
    original = runner._temporary_firewall_rules(
        [],
        port=28080,
        learner_ips=["203.0.113.10", "203.0.113.11"],
    )

    rules = runner._temporary_firewall_rules(
        original,
        port=28080,
        learner_ips=["203.0.113.10", "203.0.113.11"],
    )

    assert rules == original
