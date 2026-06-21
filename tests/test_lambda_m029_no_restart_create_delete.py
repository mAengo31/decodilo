from pathlib import Path

from decodilo.lambda_cloud.endpoint_policy import LambdaEndpoint, LambdaEndpointPolicy
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard


def test_m029_policy_denies_restart_create_delete():
    policy = LambdaEndpointPolicy(mode="m029_first_launch", allow_non_get=True)
    for operation, path in [
        ("restart_instance", "/instance-operations/restart"),
        ("create_ssh_key", "/ssh-keys"),
        ("delete_ssh_key", "/ssh-keys/key"),
        ("create_filesystem", "/filesystems"),
        ("delete_filesystem", "/filesystems/fs"),
    ]:
        report = policy.check(LambdaEndpoint(operation=operation, method="POST", path=path))
        assert report.allowed is False
        guard = LambdaMutationGuard().check_m029(operation, armed=True)
        assert guard.allowed is False


def test_m029_cli_exposes_no_restart_create_delete_commands():
    text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")
    assert "m029 restart" not in text
    assert "m029 create" not in text
    assert "m029 delete" not in text
