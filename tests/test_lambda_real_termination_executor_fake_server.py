from lambda_m029_helpers import m029_fixture


def test_termination_executor_fake_success_and_timeout_reconcile(tmp_path):
    fx = m029_fixture(tmp_path)
    launch, ledger = fx["launch_executor"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )

    term, ledger = fx["termination_executor"].terminate_owned_instance(
        owned_instance_id=launch.owned_instance_id,
        ledger=ledger,
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
    )

    assert term.termination_verified is True
    assert ledger.termination_verified is True

    timeout_dir = tmp_path / "timeout"
    timeout_dir.mkdir()
    fx2 = m029_fixture(timeout_dir)
    launch2, ledger2 = fx2["launch_executor"].launch_one_instance(
        resource_lock=fx2["resource"],
        arming_token=fx2["token"],
        idempotency_key=fx2["idempotency"].launch_key.idempotency_key,
    )
    term2, ledger2 = fx2["termination_executor"].terminate_owned_instance(
        owned_instance_id=launch2.owned_instance_id,
        ledger=ledger2,
        arming_token=fx2["token"],
        idempotency_key=fx2["idempotency"].terminate_key.idempotency_key,
        failure_mode="terminate_timeout_but_terminated",
    )

    assert term2.response_received is False
    assert term2.termination_verified is True
    assert ledger2.termination_verified is True
