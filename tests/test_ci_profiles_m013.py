import subprocess
import sys

import pytest

pytestmark = pytest.mark.lifecycle


def test_lifecycle_marker_configured_and_summary_includes_quick_command(pytestconfig) -> None:
    markers = "\n".join(pytestconfig.getini("markers"))
    assert "lifecycle" in markers

    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "dev", "test-profile-summary"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "not lifecycle" in completed.stdout

