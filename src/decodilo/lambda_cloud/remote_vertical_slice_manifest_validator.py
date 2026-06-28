"""Compatibility exports for M066R command-manifest validation."""

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    LambdaRemoteVerticalSliceManifestValidation,
    build_lambda_remote_vertical_slice_default_manifest,
    load_lambda_remote_vertical_slice_command_manifest,
    load_lambda_remote_vertical_slice_manifest_validation,
    validate_lambda_remote_vertical_slice_manifest,
    validate_lambda_remote_vertical_slice_manifest_from_paths,
    write_lambda_remote_vertical_slice_command_manifest,
    write_lambda_remote_vertical_slice_manifest_validation,
)

__all__ = [
    "LambdaRemoteVerticalSliceCommandEntry",
    "LambdaRemoteVerticalSliceCommandManifest",
    "LambdaRemoteVerticalSliceManifestValidation",
    "build_lambda_remote_vertical_slice_default_manifest",
    "load_lambda_remote_vertical_slice_command_manifest",
    "load_lambda_remote_vertical_slice_manifest_validation",
    "validate_lambda_remote_vertical_slice_manifest",
    "validate_lambda_remote_vertical_slice_manifest_from_paths",
    "write_lambda_remote_vertical_slice_command_manifest",
    "write_lambda_remote_vertical_slice_manifest_validation",
]
