from pathlib import Path

from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    audit_lambda_real_mutation_skeleton,
)


def test_skeleton_audit_passes_current_project() -> None:
    report = audit_lambda_real_mutation_skeleton(".")

    assert report.passed is True
    assert report.real_mutation_code_detected is False
    assert report.launch_allowed is False


def test_skeleton_audit_detects_synthetic_executable_transport(tmp_path) -> None:
    lambda_dir = tmp_path / "src" / "decodilo" / "lambda_cloud"
    lambda_dir.mkdir(parents=True)
    (lambda_dir / "real_read_only_transport.py").write_text("", encoding="utf-8")
    (lambda_dir / "bad.py").write_text(
        "class ExecutableLambdaRealMutationTransport: pass\n"
        "def x():\n"
        "    requests.post('https://lambda.invalid')\n",
        encoding="utf-8",
    )

    report = audit_lambda_real_mutation_skeleton(tmp_path)

    assert report.passed is False
    assert report.real_mutation_code_detected is True


def test_skeleton_audit_report_serializes() -> None:
    text = audit_lambda_real_mutation_skeleton(Path(".")).to_json()

    assert "mutation skeleton present but disabled" in text
