from __future__ import annotations

from lambda_m067s_helpers import (
    write_m067r_artifacts,
    write_price_snapshot,
    write_ssh_history_reports,
)

from decodilo.lambda_cloud.m067s_report import build_lambda_m067s_report_from_paths
from decodilo.lambda_cloud.remote_vertical_slice_closeout import (
    build_lambda_remote_vertical_slice_closeout_from_paths,
    write_lambda_remote_vertical_slice_closeout,
)
from decodilo.lambda_cloud.remote_vertical_slice_reconciliation import (
    build_lambda_remote_vertical_slice_reconciliation_from_paths,
    write_lambda_remote_vertical_slice_reconciliation,
)
from decodilo.lambda_cloud.remote_vslice_candidate_selector import (
    build_lambda_remote_vslice_candidate_selection_from_paths,
    write_lambda_remote_vslice_candidate_selection,
)
from decodilo.lambda_cloud.remote_vslice_retry_authorization import (
    build_lambda_remote_vslice_retry_authorization_from_path,
    write_lambda_remote_vslice_retry_authorization,
)
from decodilo.lambda_cloud.remote_vslice_retry_decision import (
    build_lambda_remote_vslice_retry_decision_from_path,
    write_lambda_remote_vslice_retry_decision,
)
from decodilo.lambda_cloud.ssh_proven_candidate_policy import (
    build_lambda_ssh_proven_candidate_policy_from_path,
    write_lambda_ssh_proven_candidate_policy,
)
from decodilo.lambda_cloud.ssh_readiness_history import (
    build_lambda_ssh_readiness_history,
    write_lambda_ssh_readiness_history,
)


def test_m067s_report_passes_for_pre_manifest_ssh_failure_closeout(tmp_path):
    paths = write_m067r_artifacts(tmp_path)
    closeout_path = tmp_path / "closeout.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    history_path = tmp_path / "history.json"
    policy_path = tmp_path / "policy.json"
    selection_path = tmp_path / "selection.json"
    decision_path = tmp_path / "decision.json"
    authorization_path = tmp_path / "authorization.json"
    write_lambda_remote_vertical_slice_closeout(
        closeout_path,
        build_lambda_remote_vertical_slice_closeout_from_paths(
            workdir=paths["workdir"],
            evidence=paths["evidence"],
            post_discovery=paths["post"],
        ),
    )
    write_lambda_remote_vertical_slice_reconciliation(
        reconciliation_path,
        build_lambda_remote_vertical_slice_reconciliation_from_paths(
            workdir=paths["workdir"],
            closeout=closeout_path,
        ),
    )
    write_lambda_ssh_readiness_history(
        history_path,
        build_lambda_ssh_readiness_history(
            report_paths=write_ssh_history_reports(tmp_path)
        ),
    )
    write_lambda_ssh_proven_candidate_policy(
        policy_path,
        build_lambda_ssh_proven_candidate_policy_from_path(history=history_path),
    )
    write_lambda_remote_vslice_candidate_selection(
        selection_path,
        build_lambda_remote_vslice_candidate_selection_from_paths(
            ssh_readiness_history=history_path,
            ssh_proven_policy=policy_path,
            price_snapshot=write_price_snapshot(tmp_path),
        ),
    )
    write_lambda_remote_vslice_retry_decision(
        decision_path,
        build_lambda_remote_vslice_retry_decision_from_path(
            candidate_selection=selection_path,
        ),
    )
    write_lambda_remote_vslice_retry_authorization(
        authorization_path,
        build_lambda_remote_vslice_retry_authorization_from_path(
            decision=decision_path,
        ),
    )

    report = build_lambda_m067s_report_from_paths(
        closeout=closeout_path,
        reconciliation=reconciliation_path,
        ssh_readiness_history=history_path,
        candidate_policy=policy_path,
        candidate_selection=selection_path,
        retry_decision=decision_path,
        authorization=authorization_path,
    )

    assert report.report_passed is True
    assert report.closeout_status == "closed_pre_manifest_ssh_port_not_reachable"
    assert report.decodilo_not_tested is True
    assert report.retry_decision_status == "wait_for_ssh_proven_candidate_live"
    assert report.launch_ready is False
    assert report.launch_allowed is False
