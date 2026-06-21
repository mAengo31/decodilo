from pathlib import Path


def test_m035_adds_no_launch_or_terminate_command_surface():
    root = Path(__file__).resolve().parents[1]
    cli_text = (root / "src" / "decodilo" / "cli.py").read_text(encoding="utf-8")

    assert "post-incident" in cli_text
    assert "post-incident launch" not in cli_text
    assert "post-incident terminate" not in cli_text
    assert "launch_ready: bool = True" not in "\n".join(
        (root / "src" / "decodilo" / "lambda_cloud" / name).read_text(
            encoding="utf-8"
        )
        for name in [
            "launch_attempt_history.py",
            "launch_endpoint_confidence_review.py",
            "launch_shape_strategy_review.py",
            "fourth_attempt_option_matrix.py",
            "m035_decision_record.py",
            "m035_report.py",
        ]
    )


def test_m035_modules_keep_billable_and_launch_flags_false():
    root = Path(__file__).resolve().parents[1]
    text = "\n".join(
        (root / "src" / "decodilo" / "lambda_cloud" / name).read_text(
            encoding="utf-8"
        )
        for name in [
            "post_incident_launch_strategy.py",
            "support_evidence_request.py",
            "fourth_attempt_risk_review.py",
        ]
    )

    assert "launch_allowed: bool = False" in text
    assert "billable_action_performed: bool = False" in text
    assert "billable_action_performed: bool = True" not in text
