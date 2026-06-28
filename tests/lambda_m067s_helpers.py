from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_m067r_artifacts(tmp_path: Path) -> dict[str, Path]:
    workdir = tmp_path / "m067r"
    report = {
        "billable_action_performed": True,
        "download_attempted": False,
        "errors": ["ssh_port_not_reachable"],
        "file_transfer_attempted": False,
        "host_discovery_status": "FOUND",
        "launch_request_sent": True,
        "owned_instance_id_redacted": "abc123...def0",
        "package_install_attempted": False,
        "readonly_verify_running_result": "running",
        "remote_command_attempted": False,
        "remote_command_result": "not_attempted",
        "remote_command_stage_results": [],
        "selected_candidate": "gpu_1x_h100_sxm5",
        "selected_region": "us-south-2",
        "source_bundle_upload_attempted": False,
        "ssh_attempted": False,
        "ssh_auth_result": "ssh_port_not_reachable",
        "ssh_port_reachable": False,
        "termination_verified": True,
        "training_attempted": False,
        "vertical_slice_status": "ssh_port_not_reachable",
    }
    evidence = {
        "host_discovery_status": "FOUND",
        "source_bundle_upload_attempted": False,
        "remote_command_attempted": False,
        "vertical_slice_status": "ssh_port_not_reachable",
    }
    post = {
        "instance_count": 0,
        "unmanaged_count": 0,
        "manual_review_required": False,
        "billable_action_performed": False,
    }
    return {
        "workdir": workdir,
        "report": write_json(workdir / "report.json", report),
        "evidence": write_json(workdir / "remote-vslice-evidence.json", evidence),
        "post": write_json(tmp_path / "post-summary.json", post),
    }


def write_ssh_history_reports(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for milestone in ("m057", "m059", "m061", "m063", "m065"):
        paths.append(
            write_json(
                tmp_path / milestone / "report.json",
                {
                    "run_id": f"lambda-{milestone}-success",
                    "launch_request_sent": True,
                    "readonly_verify_running_result": "running",
                    "host_discovery_status": "FOUND",
                    "ssh_port_reachable": True,
                    "ssh_attempted": True,
                    "ssh_auth_result": "remote_command_succeeded",
                    "remote_command_result": "succeeded",
                    "selected_candidate": "gpu_1x_a10",
                    "selected_region": "us-east-1",
                    "termination_verified": True,
                },
            )
        )
    paths.append(
        write_json(
            tmp_path / "m067r" / "report.json",
            {
                "run_id": "lambda-m067r-source-bundle-vertical-slice",
                "errors": ["ssh_port_not_reachable"],
                "launch_request_sent": True,
                "readonly_verify_running_result": "running",
                "host_discovery_status": "FOUND",
                "ssh_port_reachable": False,
                "ssh_attempted": False,
                "ssh_auth_result": "ssh_port_not_reachable",
                "remote_command_result": "not_attempted",
                "selected_candidate": "gpu_1x_h100_sxm5",
                "selected_region": "us-south-2",
                "termination_verified": True,
                "vertical_slice_status": "ssh_port_not_reachable",
            },
        )
    )
    return paths


def write_live_discovery(tmp_path: Path, pairs: list[tuple[str, str]]) -> Path:
    instance_types = [
        {"name": candidate, "regions": [{"name": region}]} for candidate, region in pairs
    ]
    return write_json(tmp_path / "discovery.json", {"instance_types": instance_types})


def write_price_snapshot(tmp_path: Path) -> Path:
    return write_json(tmp_path / "prices.json", {"prices": []})
