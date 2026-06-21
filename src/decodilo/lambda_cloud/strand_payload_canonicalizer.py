"""Canonical Strand-compatible launch payload helper."""

from __future__ import annotations

from decodilo.lambda_cloud.strand_cli_request_shapes import validate_strand_launch_payload


def canonicalize_strand_launch_payload(
    *,
    region_name: str,
    instance_type_name: str,
    ssh_key_name: str,
    quantity: int = 1,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "region_name": region_name,
        "instance_type_name": instance_type_name,
        "ssh_key_names": [ssh_key_name],
        "quantity": quantity,
    }
    validate_strand_launch_payload(payload)
    return payload
