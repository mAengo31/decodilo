from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.final_resource_lock import (
    LambdaFinalResourceLock,
    build_lambda_final_resource_lock,
)


def test_final_resource_lock_builds(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    lock = build_lambda_final_resource_lock(paths["m020"])

    assert lock.resource_lock_passed is True
    assert lock.terminate_scope == "future_owned_instance_only"
    assert lock.launch_ready is False


def test_unowned_terminate_scope_rejected():
    try:
        LambdaFinalResourceLock(
            m020_report_ref="m020",
            planned_region="us-west-1",
            planned_instance_type="gpu_8x_h100_sxm",
            planned_gpu_type="H100 SXM",
            planned_gpus_per_instance=8,
            terminate_scope="unowned",
            lock_hash="hash",
            resource_lock_passed=False,
        )
    except ValueError as exc:
        assert "future owned" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unowned terminate scope should be rejected")
