from pathlib import Path


def test_m034d_adds_no_new_launch_cli_surface():
    root = Path(__file__).resolve().parents[1]
    cli_text = (root / "src" / "decodilo" / "cli.py").read_text(encoding="utf-8")

    assert "lambda m034 incident" not in cli_text
    assert "validate-crash-safe" in cli_text
    assert "console-confirmation" in cli_text
    assert "future-launch-hold" in cli_text
    assert "m034 run" not in cli_text
    assert "m034 launch" not in cli_text


def test_m034d_modules_keep_launch_flags_false():
    root = Path(__file__).resolve().parents[1]
    module_text = "\n".join(
        (root / "src" / "decodilo" / "lambda_cloud" / name).read_text(
            encoding="utf-8"
        )
        for name in [
            "m034_incident_report.py",
            "m034_incident_closeout.py",
            "m034_future_launch_hold.py",
            "crash_safe_transport_diagnostics.py",
        ]
    )

    assert "launch_ready: bool = False" in module_text
    assert "launch_allowed: bool = False" in module_text
    assert "launch_allowed: bool = True" not in module_text
    assert "launch_ready: bool = True" not in module_text
