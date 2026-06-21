from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs


def test_known_fixture_endpoints_pass_without_live_call():
    launch = build_lambda_endpoint_spec(
        operation="launch_one_instance",
        method="POST",
        path_template="/instance-operations/launch",
        confidence="medium",
    )
    terminate = build_lambda_endpoint_spec(
        operation="terminate_owned_instance",
        method="DELETE",
        path_template="/instances/{id}",
        confidence="medium",
    )

    report = verify_lambda_endpoint_specs([launch, terminate])

    assert report.endpoint_verification_passed is True
    assert report.live_mutation_call_performed is False
    assert set(report.verified_operations) == {
        "launch_one_instance",
        "terminate_owned_instance",
    }


def test_unknown_confidence_and_non_allowed_method_block():
    spec = build_lambda_endpoint_spec(
        operation="launch_one_instance",
        method="GET",
        path_template="/instance-operations/launch",
        confidence="unknown",
    )

    report = verify_lambda_endpoint_specs([spec])

    assert report.endpoint_verification_passed is False
    assert "launch endpoint method must be POST" in report.blockers
    assert "launch_one_instance endpoint confidence too low" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
