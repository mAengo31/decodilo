from pathlib import Path


def test_m036_adds_no_launch_or_terminate_command_surface():
    root = Path(__file__).resolve().parents[1]
    cli_text = (root / "src" / "decodilo" / "cli.py").read_text(encoding="utf-8")

    assert "support-confirmation" in cli_text
    assert "lower-cost-shape" in cli_text
    assert "support-confirmation launch" not in cli_text
    assert "support-confirmation terminate" not in cli_text
    assert "lower-cost-shape launch" not in cli_text


def test_m036_modules_keep_billable_and_launch_flags_false():
    root = Path(__file__).resolve().parents[1]
    text = "\n".join(
        (root / "src" / "decodilo" / "lambda_cloud" / name).read_text(
            encoding="utf-8"
        )
        for name in [
            "support_confirmation_request.py",
            "support_confirmation_response.py",
            "support_confirmation_validator.py",
            "endpoint_confidence_upgrade.py",
            "lower_cost_shape_reauthorization.py",
            "m036_strategy_decision.py",
            "m036_report.py",
        ]
    )

    assert "launch_allowed: bool = False" in text
    assert "billable_action_performed: bool = False" in text
    assert "billable_action_performed: bool = True" not in text
