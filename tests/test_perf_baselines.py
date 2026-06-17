import json
import subprocess
import sys

import pytest


@pytest.mark.perf
def test_perf_baseline_commands_write_valid_reports(tmp_path) -> None:
    commands = [
        [
            "merge-benchmark",
            "--workdir",
            str(tmp_path / "merge"),
            "--elements",
            "128",
            "--learners",
            "3",
            "--chunk-size-kb",
            "4",
            "--dtype",
            "float32",
            "--outer-lr",
            "0.7",
            "--out",
            str(tmp_path / "merge" / "report.json"),
        ],
        [
            "artifact-io",
            "--workdir",
            str(tmp_path / "io"),
            "--total-mb",
            "1",
            "--chunk-size-kb",
            "64",
            "--out",
            str(tmp_path / "io" / "report.json"),
        ],
        [
            "compare-codecs",
            "--workdir",
            str(tmp_path / "codecs"),
            "--elements",
            "128",
            "--out",
            str(tmp_path / "codecs" / "report.json"),
        ],
    ]
    for command in commands:
        completed = subprocess.run(
            [sys.executable, "-m", "decodilo.cli", "perf", *command],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        summary = json.loads(completed.stdout)
        report = json.loads(summary["out"] and open(summary["out"], encoding="utf-8").read())
        assert summary["validation_passed"] is True
        assert report["validation_passed"] is True
        assert report["wall_time_seconds"] >= 0
        assert report["throughput_bytes_per_second"] >= 0
