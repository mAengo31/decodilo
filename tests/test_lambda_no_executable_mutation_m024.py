from pathlib import Path

from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
)
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    audit_lambda_real_mutation_skeleton,
)


def test_m024_absence_audits_pass() -> None:
    absence = audit_real_lambda_mutation_absence(".")
    skeleton = audit_lambda_real_mutation_skeleton(".")

    assert absence.passed is True
    assert skeleton.passed is True
    assert absence.launch_allowed is False
    assert skeleton.launch_allowed is False


def test_m024_live_read_only_transport_has_no_mutating_methods() -> None:
    text = Path("src/decodilo/lambda_cloud/real_read_only_transport.py").read_text(
        encoding="utf-8"
    )

    for pattern in ['"POST"', '"PUT"', '"PATCH"', '"DELETE"', "method='POST'", "method='DELETE'"]:
        assert pattern not in text


def test_m024_no_enabled_mutation_status_literals() -> None:
    offenders = []
    for path in [
        *[
            item
            for item in Path("src/decodilo/lambda_cloud").glob("*.py")
            if item.name
            not in {
                "real_mutation_absence_audit.py",
                "real_mutation_skeleton_audit.py",
            }
        ],
        Path("src/decodilo/cli.py"),
    ]:
        text = path.read_text(encoding="utf-8")
        for pattern in [
            "launch_allowed=True",
            "launch_allowed = True",
            "real_mutation_enabled=True",
            "real_mutation_enabled = True",
            "mutation_armed=True",
            "mutation_armed = True",
            "real_launch_approved",
        ]:
            if pattern in text:
                offenders.append(f"{path}:{pattern}")

    assert offenders == []
