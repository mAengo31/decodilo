import pytest
from m010_binary_helpers import run_binary_local

from decodilo.syncer.recovery_manifest import load_recovery_manifest

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_binary_chunked_syncer_checkpoint_recovery_is_primary_and_validated(tmp_path) -> None:
    report = run_binary_local(tmp_path, restart=True)

    assert report["recovery_source"] == "chunked"
    assert report["final_global_version"] >= 2
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert not (tmp_path / "syncer_checkpoint.json").exists()
    recovery_manifest = load_recovery_manifest(tmp_path / "recovery_manifest.json")
    assert recovery_manifest.recovery_source == "chunked"
    assert recovery_manifest.checkpoint_ref["manifest_path"].endswith(
        ".artifact.json"
    )
    assert "syncer_checkpoint-v" in recovery_manifest.checkpoint_ref["manifest_path"]
