from __future__ import annotations

from lambda_m070_helpers import make_bundle, make_discovery

from decodilo.lambda_cloud.first_experiment_manifest import (
    build_lambda_first_experiment_manifest_from_paths,
    write_lambda_first_experiment_manifest,
)
from decodilo.lambda_cloud.first_experiment_readiness import (
    LambdaFirstExperimentReadiness,
    write_lambda_first_experiment_readiness,
)
from decodilo.lambda_cloud.m071r_first_experiment_authorization import (
    build_lambda_m071r_first_experiment_authorization_from_paths,
)


def test_m071r_authorization_is_future_only_when_ready(tmp_path):
    readiness = tmp_path / "readiness.json"
    discovery = make_discovery(tmp_path / "discovery.json")
    manifest = tmp_path / "manifest.json"
    write_lambda_first_experiment_readiness(
        readiness,
        LambdaFirstExperimentReadiness(
            readiness_status="ready_for_future_first_experiment_planning",
            cloud_lifecycle_ready=True,
            ssh_ready=True,
            source_upload_ready=True,
            dependency_bundle_ready=True,
            decodilo_cli_ready=True,
        ),
    )
    write_lambda_first_experiment_manifest(
        manifest,
        build_lambda_first_experiment_manifest_from_paths(
            command_discovery=discovery,
            source_bundle=make_bundle(tmp_path / "source.tar.gz"),
            dependency_bundle=make_bundle(tmp_path / "deps.tar.gz", dependency=True),
        ),
    )

    auth = build_lambda_m071r_first_experiment_authorization_from_paths(
        readiness=readiness,
        command_discovery=discovery,
        manifest=manifest,
    )

    assert auth.authorization_status == "authorized_for_future_m071r_first_experiment_attempt"
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False
