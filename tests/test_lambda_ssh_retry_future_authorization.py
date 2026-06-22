from lambda_m055d_helpers import write_m055d_base_inputs

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
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    build_lambda_ssh_retry_future_authorization_from_paths,
)
from decodilo.lambda_cloud.ssh_retry_operator_decision import (
    build_lambda_ssh_retry_operator_decision_from_paths,
    write_lambda_ssh_retry_operator_decision,
)


def test_m056_authorization_is_future_only(tmp_path):
    paths = write_m055d_base_inputs(tmp_path)
    closeout = tmp_path / "ssh-closeout.json"
    history = tmp_path / "history.json"
    selection = tmp_path / "selection.json"
    policy = tmp_path / "policy.json"
    decision = tmp_path / "decision.json"
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

    report = build_lambda_ssh_retry_future_authorization_from_paths(
        capacity_closeout=closeout,
        candidate_selection=selection,
        retry_policy=policy,
        operator_decision=decision,
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m056_live_candidate_ssh_retry_review"
    )
    assert report.future_m056_review_authorized is True
    assert report.launch_authorized_now is False
    assert report.ssh_authorized_now is False
