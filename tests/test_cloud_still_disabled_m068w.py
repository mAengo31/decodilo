from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    build_lambda_linux_python310_wheelhouse_plan_from_paths,
)
from decodilo.lambda_cloud.remote_dependency_bundle import (
    LambdaRuntimeDependencyInventory,
    write_lambda_runtime_dependency_inventory,
)


def test_m068w_wheelhouse_plan_does_not_enable_cloud(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.json"
    write_lambda_runtime_dependency_inventory(
        inventory,
        LambdaRuntimeDependencyInventory(
            inventory_status="inventory_built",
            runtime_dependencies=["pydantic>=2,<3"],
            missing_runtime_dependency="pydantic",
            pydantic_required_for_cli_startup=True,
        ),
    )

    report = build_lambda_linux_python310_wheelhouse_plan_from_paths(
        inventory=inventory,
        target_python="3.10",
        target_platform="manylinux2014_x86_64",
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
