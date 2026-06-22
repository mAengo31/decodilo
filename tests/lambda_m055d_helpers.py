from __future__ import annotations

import json
from pathlib import Path

from lambda_m035_helpers import price_snapshot

from decodilo.lambda_cloud.api_models import LambdaInstanceType, LambdaSSHKey
from decodilo.lambda_cloud.capacity_error_closeout import (
    LambdaCapacityErrorCloseoutReport,
    write_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    build_lambda_ssh_stderr_capture_policy,
    write_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    select_existing_lambda_ssh_key,
    write_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import write_price_snapshot


def write_m055d_base_inputs(base: Path) -> dict[str, Path]:
    workdir = base / "m055c"
    workdir.mkdir(parents=True)
    paths = {
        "workdir": workdir,
        "run_report": workdir / "report.json",
        "capacity_closeout": base / "capacity-closeout.json",
        "post_discovery": base / "post-discovery.json",
        "live_discovery": base / "live-discovery.json",
        "price_snapshot": base / "price-snapshot.json",
        "ssh_selection": base / "ssh-selection.json",
        "stderr_policy": base / "stderr-policy.json",
    }
    paths["run_report"].write_text(
        json.dumps(
            {
                "selected_shape": "gpu_8x_a100_80gb_sxm4",
                "selected_candidate": "gpu_8x_a100_80gb_sxm4",
                "selected_region": "us-midwest-1",
                "launch_request_sent": True,
                "launch_response_received": True,
                "launch_response_http_status": 400,
                "launch_response_classification": "http_error_json",
                "launch_response_error_message_redacted": (
                    "Not enough capacity to fulfill launch request."
                ),
                "owned_instance_id_redacted": None,
                "ssh_attempted": False,
                "termination_request_sent": False,
            }
        ),
        encoding="utf-8",
    )
    write_lambda_capacity_error_closeout(
        paths["capacity_closeout"],
        LambdaCapacityErrorCloseoutReport(
            launch_request_sent=True,
            status_code=400,
            provider_error_message_redacted=(
                "Not enough capacity to fulfill launch request."
            ),
            classification="http_error_json",
            selected_shape="gpu_8x_a100_80gb_sxm4",
            selected_region="us-midwest-1",
            owned_instance_id_present=False,
            termination_required=False,
            termination_attempted=False,
            final_instance_count=0,
            final_unmanaged_count=0,
            capacity_error_confirmed=True,
            closeout_status="closed_capacity_unavailable_no_instance_created",
            closeout_succeeded=True,
            future_launch_blocked_for_same_shape=True,
            future_availability_first_required=True,
        ),
    )
    write_lambda_live_discovery_report(paths["post_discovery"], _discovery([]))
    live = _discovery(
        [
            LambdaInstanceType(
                instance_type_id="gpu_1x_a10",
                name="gpu_1x_a10",
                gpu_type="1x A10 (24 GB PCIe)",
                gpus=1,
                price_per_hour=1.29,
                regions=["us-west-1", "us-east-1"],
            ),
            LambdaInstanceType(
                instance_type_id="gpu_1x_a100_sxm4",
                name="gpu_1x_a100_sxm4",
                gpu_type="1x A100 (40 GB SXM4)",
                gpus=1,
                price_per_hour=1.99,
                regions=["us-west-2"],
            ),
            LambdaInstanceType(
                instance_type_id="gpu_8x_a100_80gb_sxm4",
                name="gpu_8x_a100_80gb_sxm4",
                gpu_type="8x A100 80GB SXM4",
                gpus=8,
                price_per_hour=22.32,
                regions=[],
            ),
        ]
    )
    write_lambda_live_discovery_report(paths["live_discovery"], live)
    write_lambda_existing_ssh_key_selection(
        paths["ssh_selection"],
        select_existing_lambda_ssh_key(discovery=live),
    )
    write_price_snapshot(paths["price_snapshot"], price_snapshot())
    write_lambda_ssh_stderr_capture_policy(
        paths["stderr_policy"],
        build_lambda_ssh_stderr_capture_policy(),
    )
    return paths


def _discovery(instance_types: list[LambdaInstanceType]) -> LambdaLiveDiscoveryReport:
    return LambdaLiveDiscoveryReport(
        source="live_read_only",
        live_api_used=True,
        instance_types=instance_types,
        ssh_keys=[
            LambdaSSHKey(
                key_id="existing-key",
                name="existing-key",
                metadata={"public_key_redacted": True},
            )
        ],
        required_endpoint_success=True,
        secret_redacted=True,
    )
