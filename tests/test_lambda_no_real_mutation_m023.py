from pathlib import Path

import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
)


def test_m023_real_mutation_absence_audit_still_passes() -> None:
    report = audit_real_lambda_mutation_absence(".")

    assert report.passed is True
    assert report.real_mutation_code_detected is False
    assert report.launch_allowed is False


def test_m023_live_transport_still_has_no_non_get_support() -> None:
    text = Path("src/decodilo/lambda_cloud/real_read_only_transport.py").read_text(
        encoding="utf-8"
    )

    assert '"POST"' not in text
    assert '"PUT"' not in text
    assert '"PATCH"' not in text
    assert '"DELETE"' not in text


def test_m023_live_client_mutation_stubs_raise_before_transport() -> None:
    client = LiveReadOnlyLambdaCloudClient(transport=object())  # type: ignore[arg-type]

    for method_name in [
        "launch_instance",
        "terminate_instance",
        "restart_instance",
        "create_ssh_key",
        "delete_ssh_key",
        "create_filesystem",
        "delete_filesystem",
    ]:
        with pytest.raises(LambdaMutationForbiddenError):
            getattr(client, method_name)()


def test_m023_no_enabled_real_launch_status_literals() -> None:
    offenders = []
    for path in [
        *[
            path
            for path in Path("src/decodilo/lambda_cloud").glob("*.py")
            if path.name != "real_mutation_absence_audit.py"
        ],
        Path("src/decodilo/cli.py"),
    ]:
        text = path.read_text(encoding="utf-8")
        for pattern in [
            "launch_allowed=True",
            "launch_allowed = True",
            "real_mutation_enabled=True",
            "real_mutation_enabled = True",
            "real_launch_approved",
        ]:
            if pattern in text:
                offenders.append(f"{path}:{pattern}")

    assert offenders == []
