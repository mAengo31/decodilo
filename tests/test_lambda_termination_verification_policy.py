from pydantic import ValidationError

from decodilo.lambda_cloud.termination_verification_policy import (
    LambdaTerminationVerificationPolicy,
    build_lambda_termination_verification_policy,
    evaluate_lambda_termination_verification_policy,
)


def test_termination_policy_requires_owned_instance_and_read_only_verification() -> None:
    report = evaluate_lambda_termination_verification_policy()

    assert report.owned_instance_id_required is True
    assert report.unowned_termination_rejected is True
    assert report.read_only_verification_required is True
    assert report.os_shutdown_insufficient is True
    assert report.launch_allowed is False


def test_termination_policy_rejects_unowned_termination() -> None:
    try:
        LambdaTerminationVerificationPolicy(allow_unowned_termination=True)
    except ValidationError as exc:
        assert "unowned termination" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unowned termination was accepted")


def test_termination_policy_states_os_shutdown_insufficient() -> None:
    policy = build_lambda_termination_verification_policy()

    assert policy.os_shutdown_is_sufficient is False
    assert '"real_termination_code_implemented": false' in policy.to_json()
