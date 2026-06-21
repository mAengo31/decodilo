from pathlib import Path

import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient


def test_live_read_only_client_mutation_methods_raise_before_transport() -> None:
    client = LiveReadOnlyLambdaCloudClient(transport=None)  # type: ignore[arg-type]

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


def test_no_real_lambda_mutation_transport_in_live_read_only_transport() -> None:
    text = Path("src/decodilo/lambda_cloud/real_read_only_transport.py").read_text(
        encoding="utf-8"
    )

    assert '"POST"' not in text
    assert '"PUT"' not in text
    assert '"PATCH"' not in text
    assert '"DELETE"' not in text


def test_fake_lifecycle_reports_no_real_mutation(tmp_path) -> None:
    from lambda_fake_lifecycle_helpers import write_approved_m020

    from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch

    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    lifecycle = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )

    assert lifecycle.real_lambda_api_used is False
    assert lifecycle.real_mutating_operations == 0
    assert lifecycle.billable_action_performed is False


def test_live_client_mutating_attribute_is_forbidden_not_executed() -> None:
    client = LiveReadOnlyLambdaCloudClient(transport=None)  # type: ignore[arg-type]

    with pytest.raises(LambdaMutationForbiddenError):
        client.launch_instance()
