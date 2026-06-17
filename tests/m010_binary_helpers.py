import json
import subprocess
import sys
from pathlib import Path


def run_binary_local(workdir: Path, *, restart: bool = False) -> dict:
    args = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "local",
        "run",
        "--learners",
        "2",
        "--steps",
        "40",
        "--min-quorum",
        "1",
        "--seed",
        "123",
        "--workdir",
        str(workdir),
        "--report-json",
        str(workdir / "report.json"),
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
        "--chunk-size-mb",
        "1",
        "--memory-budget-mb",
        "1",
        "--allow-spill-to-disk",
    ]
    if restart:
        args.extend(
            [
                "--syncer-checkpoint-interval-rounds",
                "1",
                "--restart-syncer-after-round",
                "2",
            ]
        )
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=35)
    return json.loads((workdir / "report.json").read_text(encoding="utf-8"))
