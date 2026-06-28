from __future__ import annotations

from lambda_m070_helpers import make_bundle, make_discovery

from decodilo.lambda_cloud.first_experiment_manifest import (
    build_lambda_first_experiment_manifest_from_paths,
)


def test_first_experiment_manifest_includes_discovered_command(tmp_path):
    discovery = make_discovery(tmp_path / "discovery.json")
    source = make_bundle(tmp_path / "source.tar.gz")
    dependency = make_bundle(tmp_path / "deps.tar.gz", dependency=True)

    manifest = build_lambda_first_experiment_manifest_from_paths(
        command_discovery=discovery,
        source_bundle=source,
        dependency_bundle=dependency,
    )

    stages = [entry.stage for entry in manifest.command_entries]
    assert manifest.manifest_status == "manifest_ready_for_future_review"
    assert stages[-1] == "first_experiment_command"
    assert len(stages) <= manifest.max_remote_commands
    assert manifest.no_internet_install is True
    assert manifest.no_downloads is True
    assert manifest.no_training is True
    assert manifest.launch_ready is False
    assert manifest.launch_allowed is False
