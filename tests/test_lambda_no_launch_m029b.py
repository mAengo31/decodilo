from decodilo.lambda_cloud.real_mutation_transport import LambdaM029TransportConfig


def test_m029b_does_not_enable_real_lambda_execution():
    live_url = "https://" + "cloud." + "lambdalabs." + "com/api/v1"

    try:
        LambdaM029TransportConfig(base_url=live_url)
    except ValueError as exc:
        assert "explicit real API allowance" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("M029B must not allow real Lambda mutation config")
