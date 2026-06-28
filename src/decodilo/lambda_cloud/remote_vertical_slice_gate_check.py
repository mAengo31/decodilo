"""Compatibility exports for M066R remote vertical-slice gate checks."""

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    LambdaRemoteVerticalSliceGateCheck,
    build_lambda_remote_vertical_slice_gate_check_from_paths,
    load_lambda_remote_vertical_slice_gate_check,
    write_lambda_remote_vertical_slice_gate_check,
)

__all__ = [
    "LambdaRemoteVerticalSliceGateCheck",
    "build_lambda_remote_vertical_slice_gate_check_from_paths",
    "load_lambda_remote_vertical_slice_gate_check",
    "write_lambda_remote_vertical_slice_gate_check",
]
