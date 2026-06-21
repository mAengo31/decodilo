import pytest

from decodilo.lambda_cloud.m029_termination_authorization import (
    LambdaM029TerminationAuthorization,
    build_lambda_m029_termination_authorization,
)


def test_m029_termination_authorization_owned_only():
    authorization = build_lambda_m029_termination_authorization()

    assert authorization.terminate_only_owned_instance is True
    assert authorization.verify_termination_required is True
    assert authorization.launch_allowed is False


def test_unowned_termination_rejected():
    with pytest.raises(ValueError):
        LambdaM029TerminationAuthorization(terminate_unowned_forbidden=False)

