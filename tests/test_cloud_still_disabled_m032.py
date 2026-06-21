import re
from pathlib import Path


def test_m032_does_not_enable_cloud_launch_flags():
    root = Path("src/decodilo")
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))

    assert not re.search(r"(?<![\"'])\blaunch_ready\s*[:=]\s*True\b", text)
    assert not re.search(r"(?<![\"'])\blaunch_allowed\s*[:=]\s*True\b", text)
    assert not re.search(r"(?<![\"'])\breal_mutation_enabled\s*[:=]\s*True\b", text)
    assert "execute_now" not in text


def test_m032_response_loss_commands_are_not_real_launch_commands():
    cli_text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "response-loss" in cli_text
    assert "response-loss run" not in cli_text
    assert "response-loss launch" not in cli_text
