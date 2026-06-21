from pathlib import Path

from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
)
from decodilo.lambda_cloud.semantic_mutation_audit import (
    audit_lambda_semantic_mutation_absence,
)


def test_m027_real_mutation_absence_audit_passes_current_project():
    report = audit_real_lambda_mutation_absence(".")

    assert report.passed is True
    assert report.real_mutation_code_detected is False
    assert report.launch_allowed is False


def test_m027_semantic_mutation_audit_passes_current_project():
    report = audit_lambda_semantic_mutation_absence(".")

    assert report.passed is True
    assert report.real_mutation_enabled is False


def test_m027_no_forbidden_enabled_literals_in_source():
    patterns = [
        "launch_allowed" + "=True",
        "launch_allowed" + " = True",
        "launch_ready" + "=True",
        "launch_ready" + " = True",
        "real_mutation_enabled" + "=True",
        "real_mutation_enabled" + " = True",
        "real_lambda_mutation_performed" + "=true",
    ]
    offenders = []
    for path in [*Path("src/decodilo/lambda_cloud").glob("*.py"), Path("src/decodilo/cli.py")]:
        if path.name in {
            "real_mutation_absence_audit.py",
            "real_mutation_skeleton_audit.py",
            "semantic_mutation_audit.py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern in text:
                offenders.append(f"{path}:{pattern}")
    assert offenders == []


def test_live_transport_still_get_only():
    text = Path("src/decodilo/lambda_cloud/real_read_only_transport.py").read_text(
        encoding="utf-8"
    )

    assert '"POST"' not in text
    assert '"PUT"' not in text
    assert '"PATCH"' not in text
    assert '"DELETE"' not in text
