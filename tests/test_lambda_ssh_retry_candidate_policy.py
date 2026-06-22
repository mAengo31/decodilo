from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.ssh_capacity_history import (
    build_lambda_ssh_capacity_history_from_paths,
    write_lambda_ssh_capacity_history,
)
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
    write_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    build_lambda_ssh_retry_candidate_policy_from_paths,
)


def test_ssh_retry_candidate_policy_requires_redacted_stderr_capture(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)
    closeout = tmp_path / "ssh-closeout.json"
    history = tmp_path / "history.json"
    write_lambda_ssh_capacity_retry_closeout(
        closeout,
        build_lambda_ssh_capacity_retry_closeout_from_paths(
            workdir=paths["workdir"],
            capacity_closeout=paths["capacity_closeout"],
            post_discovery=paths["post_discovery"],
        ),
    )
    write_lambda_ssh_capacity_history(
        history,
        build_lambda_ssh_capacity_history_from_paths(
            latest_closeout=closeout,
            prior_m055b_report=tmp_path / "missing.json",
        ),
    )

    report = build_lambda_ssh_retry_candidate_policy_from_paths(
        capacity_history=history,
        stderr_policy=paths["stderr_policy"],
    )

    assert report.policy_status == "policy_passed"
    assert report.no_automatic_retry is True
    assert report.max_ssh_attempts == 1
    assert report.no_remote_command is True
    assert report.launch_allowed is False
