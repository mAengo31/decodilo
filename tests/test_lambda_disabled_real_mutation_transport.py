import pytest

from decodilo.lambda_cloud.disabled_real_mutation_transport import (
    DisabledLambdaRealMutationTransport,
    LambdaRealMutationDisabledError,
)


def test_launch_raises_before_request_construction() -> None:
    transport = DisabledLambdaRealMutationTransport()

    with pytest.raises(LambdaRealMutationDisabledError) as exc:
        transport.launch_one_instance()

    report = exc.value.report
    assert report.blocked_before_request_construction is True
    assert report.url_constructed is False
    assert report.request_body_constructed is False
    assert report.credential_accessed is False
    assert report.network_accessed is False
    assert report.launch_allowed is False


def test_all_disabled_transport_mutations_raise() -> None:
    transport = DisabledLambdaRealMutationTransport()

    for method_name in [
        "terminate_owned_instance",
        "restart_instance",
        "create_ssh_key",
        "delete_ssh_key",
        "create_filesystem",
        "delete_filesystem",
    ]:
        with pytest.raises(LambdaRealMutationDisabledError):
            getattr(transport, method_name)()


def test_disabled_report_serializes() -> None:
    transport = DisabledLambdaRealMutationTransport()
    result = transport.disabled_result("launch_one_instance")

    assert result.request_constructed is False
    assert '"real_lambda_api_used": false' in result.to_json()
