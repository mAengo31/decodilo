from __future__ import annotations

import pytest

from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    LambdaParameterFragmentCommandDiscovery,
    discover_lambda_parameter_fragment_command,
)


def test_parameter_fragment_discovery_finds_safe_smoke_command():
    report = discover_lambda_parameter_fragment_command(source_root=".")

    assert report.discovery_status == "found_safe_parameter_fragment_command"
    assert report.command_category == "dev_parameter_fragment_smoke_two_fragments_one_step"
    assert report.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "parameter-fragment-smoke",
        "--synthetic",
        "--fragments",
        "2",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-parameter-fragment-smoke.json",
    ]
    assert report.expected_parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.synthetic_only is True
    assert report.fragments == 2
    assert report.max_steps == 1
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_parameter_fragment_discovery_rejects_unsafe_flags():
    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="found_safe_parameter_fragment_command",
            argv_tokens=["unsafe"],
            overlap_claim_allowed=True,
            expected_parameter_fragment_semantics="synthetic_vector_fragments",
        )


def test_parameter_fragment_discovery_rejects_unverified_fragment_semantics():
    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="found_safe_parameter_fragment_command",
            argv_tokens=["unsafe"],
            expected_parameter_fragment_semantics="storage_chunk_only",
        )
