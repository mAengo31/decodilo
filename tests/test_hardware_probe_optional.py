import json
import subprocess
import sys

import pytest


@pytest.mark.hardware_optional
def test_hardware_probe_cli_works_without_accelerator_requirement() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "hardware", "probe"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["cpu_available"] is True
    assert "torch_available" in payload
    assert payload["selected_device"] == "cpu"

