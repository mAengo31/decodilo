from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.real_termination_verifier import (
    verify_m029_owned_instance_terminated,
)


def test_real_termination_verifier_uses_read_only_get(tmp_path):
    fx = m029_fixture(tmp_path)
    launch, ledger = fx["launch_executor"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )
    fx["termination_executor"].terminate_owned_instance(
        owned_instance_id=launch.owned_instance_id,
        ledger=ledger,
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
    )

    report = verify_m029_owned_instance_terminated(
        transport=fx["transport"],
        arming_token=fx["token"],
        owned_instance_id=launch.owned_instance_id,
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
    )

    assert report.verification_passed is True
    assert report.os_shutdown_used is False
