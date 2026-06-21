from decodilo.lambda_cloud.launch_plan import execute_lambda_launch_plan
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard


def test_lambda_m020_keeps_mutation_guard_fail_closed() -> None:
    guard = LambdaMutationGuard()

    assert guard.check("list_instances").allowed is True
    assert guard.check("launch_instance").allowed is False
    assert guard.check("terminate_instance").allowed is False
    assert guard.check("unknown_future_mutation").allowed is False


def test_lambda_m020_has_no_launch_execution_path() -> None:
    from decodilo.errors import LaunchDisabledError
    from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan

    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
    )

    try:
        execute_lambda_launch_plan(plan)
    except LaunchDisabledError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Lambda launch execution unexpectedly succeeded")
