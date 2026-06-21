"""Offline Strand-AI lambda-cli behavioral fixtures.

The Strand CLI is unofficial. These constants are behavioral evidence from a
known-working operator-tested implementation, not Lambda support evidence.
"""

from __future__ import annotations

from typing import Final

STRAND_CLI_REPO_URL: Final[str] = "https://github.com/Strand-AI/lambda-cli"
STRAND_API_BASE_URL: Final[str] = "https://cloud.lambdalabs.com/api/v1"
STRAND_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
STRAND_AUTH_SCHEME: Final[str] = "Authorization: Bearer <api_key>"
STRAND_LIST_INSTANCE_TYPES: Final[str] = "/instance-types"
STRAND_LIST_INSTANCES: Final[str] = "/instances"
STRAND_GET_INSTANCE: Final[str] = "/instances/{instance_id}"
STRAND_LAUNCH_ENDPOINT: Final[str] = "/instance-operations/launch"
STRAND_TERMINATE_ENDPOINT: Final[str] = "/instance-operations/terminate"
STRAND_LAUNCH_METHOD: Final[str] = "POST"
STRAND_TERMINATE_METHOD: Final[str] = "POST"
STRAND_READ_METHOD: Final[str] = "GET"
STRAND_REQUIRED_LAUNCH_FIELDS: Final[tuple[str, ...]] = (
    "region_name",
    "instance_type_name",
    "ssh_key_names",
    "quantity",
)
STRAND_OPTIONAL_LAUNCH_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "file_system_names",
)
STRAND_TERMINATE_FIELDS: Final[tuple[str, ...]] = ("instance_ids",)
