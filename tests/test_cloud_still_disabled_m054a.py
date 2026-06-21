from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo import cli
from decodilo.lambda_cloud.m054a_report import build_lambda_m054a_report_from_paths


def test_m054a_keeps_cloud_launch_and_ssh_disabled(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_m054a_report_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        reviewer_bridge=paths["reviewer_bridge"],
        no_exec_audit=paths["no_exec_audit"],
        command_preview=paths["command_preview"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_m029_run_requires_complete_m054b_artifacts_before_execution(tmp_path):
    paths = write_m054a_inputs(tmp_path)
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "lambda",
            "m029",
            "run",
            "--workdir",
            str(tmp_path / "workdir"),
            "--m054-ssh-one-shot-arming",
            str(paths["one_shot_arming"]),
            "--m054-ssh-reviewer-bridge",
            str(paths["reviewer_bridge"]),
            "--m054-ssh-static-validation",
            str(paths["static_validation"]),
            "--m054-ssh-no-exec-audit",
            str(paths["no_exec_audit"]),
            "--m054-ssh-command-preview",
            str(paths["command_preview"]),
        ]
    )

    try:
        args.func(args)
    except SystemExit as exc:
        assert "requires all M054B artifacts" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("partial M054B flags must halt before request construction")
