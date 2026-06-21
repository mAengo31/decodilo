from lambda_m029_helpers import m029_fixture


def test_launch_executor_fake_success_and_timeout_reconcile(tmp_path):
    fx = m029_fixture(tmp_path)

    result, ledger = fx["launch_executor"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )

    assert result.request_sent is True
    assert result.owned_instance_id.startswith("fake-i-")
    assert ledger.can_terminate(result.owned_instance_id)

    timeout_dir = tmp_path / "timeout"
    timeout_dir.mkdir()
    fx2 = m029_fixture(timeout_dir)
    result2, ledger2 = fx2["launch_executor"].launch_one_instance(
        resource_lock=fx2["resource"],
        arming_token=fx2["token"],
        idempotency_key=fx2["idempotency"].launch_key.idempotency_key,
        failure_mode="launch_timeout_but_created",
    )

    assert result2.response_received is False
    assert result2.owned_instance_id.startswith("fake-i-")
    assert ledger2.can_terminate(result2.owned_instance_id)
