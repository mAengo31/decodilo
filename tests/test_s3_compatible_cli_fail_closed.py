"""CLI/subprocess fail-closed behavior for the S3-compatible artifact backend.

The live local/Lambda runtime spawns the syncer and learners as CLI subprocesses.
That boundary cannot inject a Python S3 client object, so selecting
``--artifact-storage-backend s3_compatible`` there must fail *cleanly and early*
with a clear, non-traceback error, not crash deep inside syncer shutdown.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_local_run_rejects_s3_compatible_backend_cleanly(tmp_path: Path) -> None:
    completed = _run_cli(
        [
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "8",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--vector-dim",
            "4",
            "--fragments",
            "1",
            "--local-steps-per-sync",
            "4",
            "--payload-storage-mode",
            "chunked",
            "--global-update-storage-mode",
            "chunked",
            "--checkpoint-storage-mode",
            "chunked",
            "--merge-mode",
            "streaming_chunked",
            "--chunk-size-mb",
            "1",
            "--artifact-transfer-mode",
            "object_store",
            "--artifact-storage-backend",
            "s3_compatible",
        ]
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "s3_compatible" in combined
    assert "explicit" in combined or "not supported over the CLI" in combined
    assert "syncer shutdown failed" not in combined
    assert "Traceback (most recent call last)" not in combined


def test_syncer_serve_rejects_s3_compatible_backend_cleanly(tmp_path: Path) -> None:
    completed = _run_cli(
        [
            "syncer",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--ready-file",
            str(tmp_path / "ready.json"),
            "--workdir",
            str(tmp_path),
            "--run-id",
            "run-s3-cli",
            "--artifact-transfer-mode",
            "object_store",
            "--artifact-storage-backend",
            "s3_compatible",
        ]
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "s3_compatible" in combined
    assert "Traceback (most recent call last)" not in combined


def test_learner_run_rejects_s3_compatible_backend_cleanly(tmp_path: Path) -> None:
    completed = _run_cli(
        [
            "learner",
            "run",
            "--learner-id",
            "learner-0",
            "--run-id",
            "run-s3-cli",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--workdir",
            str(tmp_path),
            "--artifact-transfer-mode",
            "object_store",
            "--artifact-storage-backend",
            "s3_compatible",
        ]
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "s3_compatible" in combined
    assert "Traceback (most recent call last)" not in combined


def test_local_run_accepts_s3_backend_when_explicit_runtime_config_is_present(
    tmp_path: Path,
) -> None:
    completed = _run_cli(
        [
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "4",
            "--min-quorum",
            "1",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--payload-storage-mode",
            "chunked",
            "--global-update-storage-mode",
            "chunked",
            "--checkpoint-storage-mode",
            "chunked",
            "--merge-mode",
            "streaming_chunked",
            "--artifact-transfer-mode",
            "object_store",
            "--artifact-storage-backend",
            "s3_compatible",
            "--s3-endpoint-url",
            "https://object.example.invalid",
            "--s3-bucket",
            "bucket",
            "--s3-access-key-ref",
            "AWS_ACCESS_KEY_ID",
            "--s3-secret-key-ref",
            "AWS_SECRET_ACCESS_KEY",
        ]
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "not supported over the CLI" not in combined
    assert "s3_compatible" in combined or "S3" in combined
