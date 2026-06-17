import pytest

from decodilo.cloud.teardown_plan import TeardownPlan, build_dry_run_teardown_plan


def test_dry_run_teardown_plan_has_no_live_resource_ids() -> None:
    plan = build_dry_run_teardown_plan(
        provider="lambda",
        run_id="teardown",
        resources_planned=["1x gpu_8x_h100_sxm"],
        max_runtime_hours=2,
    )

    assert plan.has_live_resource_ids is False
    assert plan.live_resource_ids == []
    assert plan.teardown_verified is False


def test_teardown_plan_rejects_live_resource_ids_in_dry_run() -> None:
    with pytest.raises(ValueError, match="live resource IDs"):
        TeardownPlan(
            provider="lambda",
            run_id="teardown",
            max_runtime_hours=1,
            has_live_resource_ids=True,
            live_resource_ids=["i-live"],
        )

