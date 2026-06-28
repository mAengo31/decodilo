from __future__ import annotations

from lambda_m082_helpers import (
    make_m081r2_workdir,
    safe_optimizer_discovery_kwargs,
    write_m082_closeout_chain,
)

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    LambdaDilocoOptimizerCommandDiscovery,
    write_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    build_lambda_diloco_optimizer_policy_from_path,
    write_lambda_diloco_optimizer_policy,
)
from decodilo.lambda_cloud.diloco_optimizer_readiness import (
    build_lambda_diloco_optimizer_readiness_from_path,
    write_lambda_diloco_optimizer_readiness,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    build_lambda_m083r_diloco_optimizer_authorization_from_paths,
    write_lambda_m083r_diloco_optimizer_authorization,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_runbook_preview import (
    build_lambda_m083r_diloco_optimizer_runbook_preview_from_path,
)


def test_m083r_runbook_preview_blocks_without_safe_optimizer_command(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    write_lambda_diloco_optimizer_readiness(
        readiness_path,
        build_lambda_diloco_optimizer_readiness_from_path(
            diloco_synthetic_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_optimizer_command_discovery(
        discovery_path,
        LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="no_safe_diloco_optimizer_command_found",
            blockers=["no_safe_diloco_optimizer_command_found"],
        ),
    )
    write_lambda_diloco_optimizer_policy(
        policy_path,
        build_lambda_diloco_optimizer_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m083r_diloco_optimizer_authorization(
        authorization_path,
        build_lambda_m083r_diloco_optimizer_authorization_from_paths(
            diloco_synthetic_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )

    preview = build_lambda_m083r_diloco_optimizer_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "blocked_no_safe_diloco_optimizer_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m083r_runbook_preview_ready_when_optimizer_command_is_safe(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    write_lambda_diloco_optimizer_readiness(
        readiness_path,
        build_lambda_diloco_optimizer_readiness_from_path(
            diloco_synthetic_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_optimizer_command_discovery(
        discovery_path,
        LambdaDilocoOptimizerCommandDiscovery(**safe_optimizer_discovery_kwargs()),
    )
    write_lambda_diloco_optimizer_policy(
        policy_path,
        build_lambda_diloco_optimizer_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m083r_diloco_optimizer_authorization(
        authorization_path,
        build_lambda_m083r_diloco_optimizer_authorization_from_paths(
            diloco_synthetic_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )

    preview = build_lambda_m083r_diloco_optimizer_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "ready_for_future_m083r_diloco_optimizer_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
