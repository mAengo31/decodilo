from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain
from lambda_m084_helpers import (
    make_m083r_workdir,
    write_learner_syncer_closeout,
    write_m084_optimizer_closeout_chain,
)

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    LambdaIntegratedDilocoCommandDiscovery,
    write_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    build_lambda_integrated_diloco_policy_from_path,
    write_lambda_integrated_diloco_policy,
)
from decodilo.lambda_cloud.integrated_diloco_synthetic_readiness import (
    build_lambda_integrated_diloco_synthetic_readiness_from_paths,
    write_lambda_integrated_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.m084a_report import build_lambda_m084a_report_from_paths
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    build_lambda_m085r_integrated_diloco_authorization_from_paths,
    write_lambda_m085r_integrated_diloco_authorization,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_runbook_preview import (
    build_lambda_m085r_integrated_diloco_runbook_preview_from_path,
    write_lambda_m085r_integrated_diloco_runbook_preview,
)


def test_m084a_report_passes_when_m085r_future_authorized(tmp_path):
    diloco_paths = write_m082_closeout_chain(tmp_path, make_m081r2_workdir(tmp_path))
    optimizer_paths = write_m084_optimizer_closeout_chain(
        tmp_path, make_m083r_workdir(tmp_path)
    )
    learner_closeout = write_learner_syncer_closeout(tmp_path)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_integrated_diloco_synthetic_readiness(
        readiness_path,
        build_lambda_integrated_diloco_synthetic_readiness_from_paths(
            diloco_synthetic_closeout=diloco_paths["closeout"],
            optimizer_closeout=optimizer_paths["closeout"],
            learner_syncer_closeout=learner_closeout,
        ),
    )
    write_lambda_integrated_diloco_command_discovery(
        discovery_path,
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="found_safe_integrated_diloco_command",
            command_category="dev_integrated_diloco_smoke_one_step",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "integrated-diloco-smoke",
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-integrated-diloco-smoke.json",
            ],
            timeout_seconds=120,
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            expected_integrated_fidelity="integrated_optimizer_protocol_smoke",
        ),
    )
    write_lambda_integrated_diloco_policy(
        policy_path,
        build_lambda_integrated_diloco_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m085r_integrated_diloco_authorization(
        authorization_path,
        build_lambda_m085r_integrated_diloco_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m085r_integrated_diloco_runbook_preview(
        runbook_path,
        build_lambda_m085r_integrated_diloco_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m084a_report_from_paths(
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.integrated_diloco_smoke_command_added is True
    assert report.discovery_status == "found_safe_integrated_diloco_command"
    assert report.policy_status == "policy_passed"
    assert (
        report.m085r_authorization_status
        == "authorized_for_future_m085r_integrated_diloco_smoke"
    )
    assert report.runbook_preview_status == "ready_for_future_m085r_integrated_diloco_review"
    assert report.integrated_fidelity_status == "integrated_optimizer_protocol_smoke"
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
