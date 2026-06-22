from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.m055d_report import build_lambda_m055d_report_from_paths
from decodilo.lambda_cloud.ssh_capacity_history import (
    build_lambda_ssh_capacity_history_from_paths,
    write_lambda_ssh_capacity_history,
)
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
    write_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    build_lambda_ssh_live_candidate_selection_from_paths,
    write_lambda_ssh_live_candidate_selection,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    build_lambda_ssh_retry_candidate_policy_from_paths,
    write_lambda_ssh_retry_candidate_policy,
)
from decodilo.lambda_cloud.ssh_retry_command_preview import (
    build_lambda_ssh_retry_command_preview_from_path,
    write_lambda_ssh_retry_command_preview,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    build_lambda_ssh_retry_future_authorization_from_paths,
    write_lambda_ssh_retry_future_authorization,
)
from decodilo.lambda_cloud.ssh_retry_operator_decision import (
    build_lambda_ssh_retry_operator_decision_from_paths,
    write_lambda_ssh_retry_operator_decision,
)


def test_m055d_report_rolls_up_future_m056_package(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)
    closeout = tmp_path / "ssh-closeout.json"
    history = tmp_path / "history.json"
    selection = tmp_path / "selection.json"
    policy = tmp_path / "policy.json"
    decision = tmp_path / "decision.json"
    auth = tmp_path / "auth.json"
    preview = tmp_path / "preview.json"
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
    write_lambda_ssh_live_candidate_selection(
        selection,
        build_lambda_ssh_live_candidate_selection_from_paths(
            discovery_report=paths["live_discovery"],
            price_snapshot=paths["price_snapshot"],
            ssh_key_selection=paths["ssh_selection"],
            capacity_history=history,
            max_budget=50,
        ),
    )
    write_lambda_ssh_retry_candidate_policy(
        policy,
        build_lambda_ssh_retry_candidate_policy_from_paths(
            capacity_history=history,
            stderr_policy=paths["stderr_policy"],
        ),
    )
    write_lambda_ssh_retry_operator_decision(
        decision,
        build_lambda_ssh_retry_operator_decision_from_paths(
            candidate_selection=selection,
            retry_policy=policy,
        ),
    )
    write_lambda_ssh_retry_future_authorization(
        auth,
        build_lambda_ssh_retry_future_authorization_from_paths(
            capacity_closeout=closeout,
            candidate_selection=selection,
            retry_policy=policy,
            operator_decision=decision,
        ),
    )
    write_lambda_ssh_retry_command_preview(
        preview,
        build_lambda_ssh_retry_command_preview_from_path(auth),
    )

    report = build_lambda_m055d_report_from_paths(
        capacity_closeout=closeout,
        capacity_history=history,
        candidate_selection=selection,
        retry_policy=policy,
        operator_decision=decision,
        authorization=auth,
        command_preview=preview,
    )

    assert report.report_passed is True
    assert report.selected_candidate == "gpu_1x_a10"
    assert report.m056_authorization_status == (
        "authorized_for_future_m056_live_candidate_ssh_retry_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
