from lambda_m033_helpers import (
    endpoint_confirmation,
    mitigation_acceptance,
    third_attempt_authorization,
)


def test_complete_evidence_authorizes_future_m034_only():
    authorization = third_attempt_authorization()

    assert authorization.status == "authorized_for_future_m034_third_launch_attempt"
    assert authorization.m034_authorization_record.launch_authorized_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.real_mutation_enabled is False


def test_missing_mitigation_blocks_authorization():
    bad_mitigation = mitigation_acceptance().model_copy(
        update={
            "mitigation_accepted": False,
            "future_launch_hold_can_release": False,
            "blockers": ["endpoint_spec_not_verified"],
        }
    )
    authorization = third_attempt_authorization(mitigation_acceptance=bad_mitigation)

    assert authorization.status == "not_authorized"
    assert "m032_mitigation_not_accepted" in authorization.blockers


def test_missing_endpoint_confirmation_blocks_authorization():
    authorization = third_attempt_authorization(
        endpoint_confirmation=endpoint_confirmation(accept_medium=False)
    )

    assert authorization.status == "not_authorized"
    assert "endpoint_confirmation_missing" in authorization.blockers


def test_missing_renewed_operator_approval_blocks_authorization():
    authorization = third_attempt_authorization(renewed_operator_approval_present=False)

    assert authorization.status == "not_authorized"
    assert "renewed_operator_approval_missing" in authorization.blockers
