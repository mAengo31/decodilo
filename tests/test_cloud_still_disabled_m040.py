from pathlib import Path

from lambda_m040_helpers import (
    authorization,
    candidates,
    capacity_closeout,
    plan,
    rank,
)


def test_m040_artifacts_keep_launch_disabled(tmp_path):
    reports = [
        capacity_closeout(),
        candidates(),
        rank(),
        plan(),
        authorization(tmp_path),
    ]

    for report in reports:
        assert report.launch_ready is False
        assert report.launch_allowed is False
        assert report.billable_action_performed is False
        assert report.real_mutation_enabled is False


def test_m040_cli_has_no_launch_command_for_availability_first():
    cli_text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "availability-first" in cli_text
    assert "capacity-error" in cli_text
    assert "availability-first launch" not in cli_text
