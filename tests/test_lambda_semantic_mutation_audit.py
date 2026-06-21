from decodilo.lambda_cloud.semantic_mutation_audit import (
    audit_lambda_semantic_mutation_absence,
)


def test_semantic_mutation_audit_current_project_passes():
    report = audit_lambda_semantic_mutation_absence(".")

    assert report.passed is True
    assert report.launch_allowed is False


def test_semantic_mutation_audit_detects_synthetic_executable_launch(tmp_path):
    lambda_dir = tmp_path / "src" / "decodilo" / "lambda_cloud"
    lambda_dir.mkdir(parents=True)
    (lambda_dir / "bad.py").write_text(
        "def launch_instance():\n    return 'sent'\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "decodilo" / "cli.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "decodilo" / "cli.py").write_text("", encoding="utf-8")

    report = audit_lambda_semantic_mutation_absence(tmp_path)

    assert report.passed is False
    assert any("launch_instance" in blocker for blocker in report.blockers)


def test_semantic_mutation_audit_allows_disabled_method_that_raises(tmp_path):
    lambda_dir = tmp_path / "src" / "decodilo" / "lambda_cloud"
    lambda_dir.mkdir(parents=True)
    (lambda_dir / "disabled_client.py").write_text(
        "def launch_instance():\n    raise RuntimeError('disabled')\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "decodilo" / "cli.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "decodilo" / "cli.py").write_text("", encoding="utf-8")

    report = audit_lambda_semantic_mutation_absence(tmp_path)

    assert report.passed is True
    assert report.allowlisted_findings
