import json
import subprocess
import sys


def test_trainer_cli_list_check_and_matrix(tmp_path) -> None:
    listed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "trainer", "list"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    trainer_names = {entry["trainer"] for entry in json.loads(listed.stdout)["trainers"]}
    assert {"numpy_convex", "scripted"} <= trainer_names

    check_dir = tmp_path / "check"
    checked = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "trainer",
            "check",
            "--trainer",
            "numpy_convex",
            "--workdir",
            str(check_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(checked.stdout)["checks_failed"] == []

    matrix_dir = tmp_path / "matrix"
    matrix = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "trainer",
            "matrix",
            "--workdir",
            str(matrix_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(matrix.stdout)["results"]
    assert (matrix_dir / "trainer_matrix.json").exists()

