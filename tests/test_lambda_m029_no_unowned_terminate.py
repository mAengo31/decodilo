from lambda_m029_helpers import m029_fixture


def test_m029_unowned_terminate_blocked(tmp_path):
    fx = m029_fixture(tmp_path)

    try:
        fx["terminate_client"].terminate_owned_instance(
            owned_instance_id="fake-i-unowned",
            ledger=fx["ledger"],
            arming_token=fx["token"],
            idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
        )
    except ValueError as exc:
        assert "unowned" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unowned terminate should be blocked")
