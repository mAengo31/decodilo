from decodilo.lambda_cloud.real_launch_idempotency import build_m029_idempotency_report


def test_real_launch_idempotency_keys_are_deterministic_and_plan_scoped():
    one = build_m029_idempotency_report(run_id="run", plan_hash="plan-a")
    two = build_m029_idempotency_report(run_id="run", plan_hash="plan-a")
    three = build_m029_idempotency_report(run_id="run", plan_hash="plan-b")

    assert one.launch_key.idempotency_key == two.launch_key.idempotency_key
    assert one.launch_key.idempotency_key != three.launch_key.idempotency_key
    assert "launch_one_instance" in one.launch_key.idempotency_key
    assert "terminate_owned_instance" in one.terminate_key.idempotency_key
