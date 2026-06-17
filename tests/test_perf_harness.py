import json
import subprocess
import sys

import pytest


@pytest.mark.perf
def test_perf_local_overhead_cli_writes_report(tmp_path) -> None:
    out = tmp_path / "perf_report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "local-overhead",
            "--workdir",
            str(tmp_path / "run"),
            "--out",
            str(out),
            "--learners",
            "2",
            "--steps",
            "30",
            "--min-quorum",
            "1",
            "--payload-storage-mode",
            "chunked",
            "--global-update-storage-mode",
            "chunked",
            "--checkpoint-storage-mode",
            "chunked",
            "--merge-mode",
            "streaming_chunked",
            "--tensor-artifact-codec",
            "binary_v1",
            "--fragment-artifact-codec",
            "binary_v1",
            "--checkpoint-artifact-codec",
            "binary_v1",
            "--allow-spill-to-disk",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=35,
    )
    summary = json.loads(completed.stdout)
    report = json.loads(out.read_text(encoding="utf-8"))

    assert summary["replay_passed"] is True
    assert report["validation"]["replay_passed"] is True
    assert report["validation"]["metric_validation_passed"] is True
    assert report["codec_modes"]["fragment_artifact_codec"] == "binary_v1"
    assert report["derived_ratios"]["useful_tokens_per_second"] > 0
    for key in [
        "encode_time_fraction",
        "merge_time_fraction",
        "checkpoint_time_fraction",
        "artifact_io_time_fraction",
    ]:
        assert 0.0 <= report["derived_ratios"][key] <= 1.0


def test_perf_cli_rejects_invalid_codec_name(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "local-overhead",
            "--workdir",
            str(tmp_path / "run"),
            "--out",
            str(tmp_path / "perf.json"),
            "--tensor-artifact-codec",
            "pickle",
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "invalid choice" in completed.stderr
