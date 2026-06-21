from decodilo.lambda_cloud.m029_launch_correlation import (
    build_lambda_m029_launch_correlation_record,
)


def test_launch_correlation_hashes_idempotency_key():
    record = build_lambda_m029_launch_correlation_record(
        run_id="run",
        idempotency_key="secret-ish-key",
        planned_shape="gpu_8x_h100_sxm",
        planned_region="us-west-1",
    )

    assert record.idempotency_key_hash != "secret-ish-key"
    assert record.launch_allowed is False
    assert record.limitations
