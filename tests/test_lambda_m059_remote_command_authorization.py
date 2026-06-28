from __future__ import annotations

from lambda_m058_helpers import write_m057_noop_workdir

from decodilo.lambda_cloud.m059_remote_command_authorization import (
    build_lambda_m059_remote_command_authorization_from_paths,
)
from decodilo.lambda_cloud.remote_command_stage_policy import (
    build_lambda_remote_command_stage_policy,
    write_lambda_remote_command_stage_policy,
)
from decodilo.lambda_cloud.smallest_useful_command_review import (
    build_lambda_smallest_useful_command_review_from_path,
    write_lambda_smallest_useful_command_review,
)
from decodilo.lambda_cloud.ssh_noop_command_closeout import (
    build_lambda_ssh_noop_command_closeout_from_paths,
    write_lambda_ssh_noop_command_closeout,
)
from decodilo.lambda_cloud.ssh_noop_command_evidence_package import (
    build_lambda_ssh_noop_command_evidence_package_from_paths,
    write_lambda_ssh_noop_command_evidence_package,
)
from decodilo.lambda_cloud.ssh_noop_command_reconciliation import (
    build_lambda_ssh_noop_command_reconciliation_from_paths,
    write_lambda_ssh_noop_command_reconciliation,
)
from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    build_lambda_ssh_noop_command_success_record_from_paths,
    write_lambda_ssh_noop_command_success_record,
)


def _authorization_inputs(tmp_path, **kwargs):
    paths = write_m057_noop_workdir(tmp_path, **kwargs)
    success_path = tmp_path / "success.json"
    success = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )
    write_lambda_ssh_noop_command_success_record(success_path, success)
    reconciliation_path = tmp_path / "reconciliation.json"
    reconciliation = build_lambda_ssh_noop_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    write_lambda_ssh_noop_command_reconciliation(reconciliation_path, reconciliation)
    evidence_path = tmp_path / "evidence.json"
    evidence = build_lambda_ssh_noop_command_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        secret_scan=paths["secret_scan"],
    )
    write_lambda_ssh_noop_command_evidence_package(evidence_path, evidence)
    closeout_path = tmp_path / "closeout.json"
    closeout = build_lambda_ssh_noop_command_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
    )
    write_lambda_ssh_noop_command_closeout(closeout_path, closeout)
    policy_path = tmp_path / "stage-policy.json"
    write_lambda_remote_command_stage_policy(
        policy_path,
        build_lambda_remote_command_stage_policy(),
    )
    review_path = tmp_path / "review.json"
    review = build_lambda_smallest_useful_command_review_from_path(
        stage_policy=policy_path,
    )
    write_lambda_smallest_useful_command_review(review_path, review)
    return closeout_path, policy_path, review_path


def test_m059_authorization_is_future_only_for_hostname(tmp_path):
    closeout, policy, review = _authorization_inputs(tmp_path)

    auth = build_lambda_m059_remote_command_authorization_from_paths(
        ssh_noop_closeout=closeout,
        stage_policy=policy,
        command_review=review,
    )

    assert (
        auth.authorization_status
        == "authorized_for_future_m059_identity_command_review"
    )
    assert auth.selected_future_command_set == ["hostname"]
    assert auth.launch_authorized_now is False
    assert auth.command_authorized_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False


def test_m059_authorization_blocks_failed_closeout(tmp_path):
    closeout, policy, review = _authorization_inputs(
        tmp_path,
        termination_verified=False,
    )

    auth = build_lambda_m059_remote_command_authorization_from_paths(
        ssh_noop_closeout=closeout,
        stage_policy=policy,
        command_review=review,
    )

    assert auth.authorization_status == "not_authorized"
    assert "ssh_noop_closeout_not_succeeded" in auth.blockers
