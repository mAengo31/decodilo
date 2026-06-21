import json
import subprocess
import sys

from lambda_m029_helpers import m029_fixture
from lambda_m034a_helpers import m034_cli_args, write_m034a_artifacts

from decodilo.lambda_cloud.real_mutation_transport import LambdaM029TransportConfig


def test_m034_valid_test_run_uses_in_memory_fake_only(tmp_path):
    fx = m029_fixture(tmp_path)
    paths = write_m034a_artifacts(tmp_path, m029_authorization=fx["authorization"])
    workdir = tmp_path / "fake-only"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--m028-report",
        str(fx["m028_report"]),
        "--m029-authorization",
        str(fx["m029_authorization"]),
        *m034_cli_args(paths),
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
    ]

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    report = json.loads((workdir / "report.json").read_text(encoding="utf-8"))
    diagnostics = json.loads(
        (workdir / "transport-diagnostics.json").read_text(encoding="utf-8")
    )
    assert report["real_lambda_api_used"] is False
    assert report["billable_action_performed"] is False
    assert diagnostics["status_captured_before_parse"] is True
    assert all(
        item["real_lambda_api_used"] is False for item in diagnostics["diagnostics"]
    )


def test_m034_transport_config_still_rejects_real_url_without_real_allowance():
    live_host = "https://" + "cloud.lambdalabs.com"
    try:
        LambdaM029TransportConfig(
            base_url=f"{live_host}/api/v1",
            fake_server_mode=False,
            allow_real_lambda_api=False,
        )
    except ValueError as exc:
        assert "explicit real API allowance" in str(exc)
    else:  # pragma: no cover - fail loudly if guard regresses
        raise AssertionError("real Lambda URL without allowance should be rejected")
