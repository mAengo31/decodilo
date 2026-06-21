from lambda_m029_helpers import m029_fixture


def test_real_terminate_client_fake_server_terminates_owned(tmp_path):
    fx = m029_fixture(tmp_path)
    launch = fx["launch_client"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )
    owned_id = launch["data"]["instance_ids"][0]
    ledger = fx["ledger"].record_owned(
        owned_id,
        launch_attempt_id=fx["idempotency"].launch_key.idempotency_key,
    )

    result = fx["terminate_client"].terminate_owned_instance(
        owned_instance_id=owned_id,
        ledger=ledger,
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
    )

    assert result["data"]["terminated_instances"][0]["id"] == owned_id
    assert result["data"]["terminated_instances"][0]["status"] == "terminated"
