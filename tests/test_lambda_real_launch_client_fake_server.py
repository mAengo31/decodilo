from lambda_m029_helpers import m029_fixture


def test_real_launch_client_fake_server_launches_one(tmp_path):
    fx = m029_fixture(tmp_path)
    result = fx["launch_client"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )

    assert len(result["data"]["instance_ids"]) == 1
    assert result["data"]["instance_ids"][0].startswith("fake-i-")
    assert fx["transport"].audit_log[-1].request_body_redacted["quantity"] == 1
    assert fx["transport"].audit_log[-1].request_body_redacted["ssh_key_names"] == "<redacted>"
