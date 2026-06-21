from decodilo.lambda_cloud.endpoint_policy import (
    LambdaEndpoint,
    LambdaEndpointPolicy,
    endpoint_for_operation,
)


def test_endpoint_policy_allows_known_get_reads() -> None:
    policy = LambdaEndpointPolicy()

    assert policy.check(endpoint_for_operation("list_instances")).allowed
    assert policy.check(endpoint_for_operation("get_instance", instance_id="i-1")).allowed


def test_endpoint_policy_denies_mutations_unknowns_and_non_get() -> None:
    policy = LambdaEndpointPolicy()

    assert not policy.check(
        LambdaEndpoint(operation="launch_instance", method="POST", path="/instances")
    ).allowed
    assert not policy.check(
        LambdaEndpoint(operation="terminate_instance", method="DELETE", path="/instances/i-1")
    ).allowed
    assert not policy.check(
        LambdaEndpoint(operation="unknown", method="GET", path="/instances")
    ).allowed
    assert not policy.check(
        LambdaEndpoint(operation="list_instances", method="POST", path="/instances")
    ).allowed
