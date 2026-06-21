from pathlib import Path

from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
)


def _write_min_project(root: Path, *, transport_text: str = "") -> None:
    (root / "src" / "decodilo" / "lambda_cloud").mkdir(parents=True)
    (root / "src" / "decodilo" / "cloud").mkdir(parents=True)
    (root / "src" / "decodilo" / "lambda_cloud" / "real_read_only_transport.py").write_text(
        transport_text or "class T: pass\n",
        encoding="utf-8",
    )
    (root / "src" / "decodilo" / "cloud" / "disabled_launcher.py").write_text(
        "class D: pass\n",
        encoding="utf-8",
    )
    (root / "src" / "decodilo" / "cli.py").write_text("print('ok')\n", encoding="utf-8")


def test_current_project_passes_real_mutation_absence_audit() -> None:
    report = audit_real_lambda_mutation_absence(".")

    assert report.passed is True
    assert report.real_mutation_code_detected is False
    assert report.launch_allowed is False


def test_synthetic_live_post_fails_absence_audit(tmp_path) -> None:
    _write_min_project(tmp_path, transport_text='method = "POST"\n')

    report = audit_real_lambda_mutation_absence(tmp_path)

    assert report.passed is False
    assert report.live_transport_supports_post is True


def test_synthetic_cli_live_launch_fails_absence_audit(tmp_path) -> None:
    _write_min_project(tmp_path)
    (tmp_path / "src" / "decodilo" / "cli.py").write_text(
        "cmd = 'live-launch'\n",
        encoding="utf-8",
    )

    report = audit_real_lambda_mutation_absence(tmp_path)

    assert report.passed is False
    assert report.cli_has_live_launch_command is True


def test_real_mutation_absence_report_serializes() -> None:
    report = audit_real_lambda_mutation_absence(".")

    assert "real_mutation_code_detected" in report.to_json()
