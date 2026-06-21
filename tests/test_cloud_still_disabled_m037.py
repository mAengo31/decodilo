from pathlib import Path


def test_m037_adds_no_launch_or_terminate_command_surface():
    root = Path(__file__).resolve().parents[1]
    cli_text = (root / "src" / "decodilo" / "cli.py").read_text(encoding="utf-8")

    assert "m037" in cli_text
    assert "m037 launch" not in cli_text
    assert "m037 terminate" not in cli_text


def test_m037_modules_keep_billable_and_launch_flags_false():
    root = Path(__file__).resolve().parents[1]
    text = "\n".join(
        (root / "src" / "decodilo" / "lambda_cloud" / name).read_text(
            encoding="utf-8"
        )
        for name in [
            "support_response_evidence_package.py",
            "support_response_secret_scan.py",
            "endpoint_confidence_decision.py",
            "lower_cost_shape_operator_selection.py",
            "lower_cost_reauthorization_package.py",
            "m037_decision_record.py",
            "m037_report.py",
        ]
    )

    assert "launch_allowed: bool = False" in text
    assert "billable_action_performed: bool = False" in text
    assert "billable_action_performed: bool = True" not in text
