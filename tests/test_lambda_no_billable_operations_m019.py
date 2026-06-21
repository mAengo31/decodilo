from pathlib import Path

from decodilo.lambda_cloud.endpoint_policy import LambdaEndpoint, LambdaEndpointPolicy
from decodilo.lambda_cloud.read_only_audit import audit_lambda_read_only


def test_no_cli_flag_can_allow_lambda_mutation() -> None:
    source = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "--allow-mutation" not in source
    assert "--allow-launch" not in source


def test_endpoint_policy_blocks_billable_methods() -> None:
    policy = LambdaEndpointPolicy()
    for operation, method, path in [
        ("launch_instance", "POST", "/instances"),
        ("terminate_instance", "DELETE", "/instances/i-1"),
        ("restart_instance", "POST", "/instances/i-1/restart"),
        ("create_ssh_key", "POST", "/ssh-keys"),
        ("delete_ssh_key", "DELETE", "/ssh-keys/key-1"),
        ("create_filesystem", "POST", "/file-systems"),
        ("delete_filesystem", "DELETE", "/file-systems/fs-1"),
    ]:
        endpoint = LambdaEndpoint(operation=operation, method=method, path=path)
        assert not policy.check(endpoint).allowed


def test_empty_read_only_audit_has_no_billable_action() -> None:
    report = audit_lambda_read_only([])

    assert report.billable_action_performed is False
