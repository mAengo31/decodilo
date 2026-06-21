from __future__ import annotations

from pathlib import Path

from lambda_m035_helpers import price_snapshot

from decodilo.lambda_cloud.api_models import LambdaInstanceType, LambdaRegion, LambdaSSHKey
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.lower_cost_authorization_package import (
    build_lambda_lower_cost_authorization_package,
)
from decodilo.lambda_cloud.lower_cost_future_launch_decision import (
    build_lambda_lower_cost_future_launch_decision,
)
from decodilo.lambda_cloud.lower_cost_price_reconciliation import (
    reconcile_lambda_lower_cost_price,
    write_lambda_lower_cost_price_reconciliation,
)
from decodilo.lambda_cloud.lower_cost_resource_reconciliation import (
    reconcile_lambda_lower_cost_resources,
    write_lambda_lower_cost_resource_reconciliation,
)
from decodilo.lambda_cloud.m037r_report import build_lambda_m037r_report
from decodilo.lambda_cloud.strand_cli_compatibility import (
    build_strand_cli_compatibility_report,
    write_strand_cli_compatibility_report,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    build_lambda_strand_lower_cost_launch_plan,
    write_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    build_lambda_strand_response_loss_control_check,
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    select_existing_lambda_ssh_key,
    write_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import write_price_snapshot


def discovery(
    *,
    ssh_key_names: tuple[str, ...] = ("existing-key",),
    unmanaged: tuple[str, ...] = (),
    include_shape: bool = False,
) -> LambdaLiveDiscoveryReport:
    return LambdaLiveDiscoveryReport(
        source="fake_transport",
        live_api_used=False,
        regions=[LambdaRegion(region_id="us-west-1", name="us-west-1")],
        ssh_keys=[
            LambdaSSHKey(key_id=name, name=name, metadata={"public_key_redacted": True})
            for name in ssh_key_names
        ],
        instance_types=[
            LambdaInstanceType(
                instance_type_id="gpu_1x_h100_pcie",
                name="gpu_1x_h100_pcie",
                gpu_type="H100 PCIe",
                gpus=1,
            )
        ]
        if include_shape
        else [],
        unmanaged_instances=list(unmanaged),
        required_endpoint_success=True,
    )


def ssh_selection(
    *,
    ssh_key_names: tuple[str, ...] = ("existing-key",),
) -> LambdaExistingSSHKeySelectionReport:
    return select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=ssh_key_names))


def launch_plan():
    return build_lambda_strand_lower_cost_launch_plan(ssh_key_selection=ssh_selection())


def price_reconciliation(sample: bool = False):
    return reconcile_lambda_lower_cost_price(price_snapshot=price_snapshot(sample=sample))


def resource_reconciliation():
    return reconcile_lambda_lower_cost_resources(
        discovery=discovery(ssh_key_names=("existing-key",)),
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
    )


def controls():
    return build_lambda_strand_response_loss_control_check()


def write_complete_package_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "discovery": tmp_path / "discovery.json",
        "ssh": tmp_path / "ssh.json",
        "plan": tmp_path / "plan.json",
        "price": tmp_path / "price.json",
        "resource": tmp_path / "resource.json",
        "strand": tmp_path / "strand.json",
        "controls": tmp_path / "controls.json",
        "snapshot": tmp_path / "snapshot.json",
    }
    write_lambda_live_discovery_report(paths["discovery"], discovery())
    write_lambda_existing_ssh_key_selection(paths["ssh"], ssh_selection())
    write_lambda_strand_lower_cost_launch_plan_report(paths["plan"], launch_plan())
    write_lambda_lower_cost_price_reconciliation(paths["price"], price_reconciliation())
    write_lambda_lower_cost_resource_reconciliation(paths["resource"], resource_reconciliation())
    write_strand_cli_compatibility_report(paths["strand"], build_strand_cli_compatibility_report())
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    write_price_snapshot(paths["snapshot"], price_snapshot())
    return paths


def authorization_package(tmp_path: Path):
    paths = write_complete_package_inputs(tmp_path)
    return build_lambda_lower_cost_authorization_package(
        launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        price_reconciliation=paths["price"],
        resource_reconciliation=paths["resource"],
        strand_compatibility=paths["strand"],
        response_loss_controls=paths["controls"],
    )


def decision(tmp_path: Path):
    return build_lambda_lower_cost_future_launch_decision(
        authorization_package=authorization_package(tmp_path)
    )


def m037r_report(tmp_path: Path):
    return build_lambda_m037r_report(decision=decision(tmp_path))
