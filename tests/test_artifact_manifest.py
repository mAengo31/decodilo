import json
import subprocess
import sys

import pytest

from decodilo.runtime.artifact_manifest import ArtifactManifest, validate_artifact_manifest


@pytest.mark.integration
def test_artifact_manifest_includes_hashes_and_validates(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "25",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--syncer-checkpoint-interval-rounds",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    manifest = ArtifactManifest.model_validate_json(
        (tmp_path / "artifacts.json").read_text(encoding="utf-8")
    )

    assert not validate_artifact_manifest(manifest)
    assert manifest.artifacts[str(report_path)].sha256
    assert manifest.syncer_checkpoint_paths
    assert json.loads(report_path.read_text(encoding="utf-8"))["artifact_manifest_path"]
