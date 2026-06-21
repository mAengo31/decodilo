"""Disabled Lambda Cloud client."""

from __future__ import annotations

from decodilo.lambda_cloud.errors import LambdaCloudDisabledError


class DisabledLambdaCloudClient:
    """A client that proves Lambda API access remains disabled."""

    def _disabled(self, operation: str) -> None:
        raise LambdaCloudDisabledError(
            f"Lambda Cloud API operation {operation!r} is disabled; "
            "M018 only permits fixtures and local fake transports"
        )

    def list_instance_types(self) -> None:
        self._disabled("list_instance_types")

    def list_regions(self) -> None:
        self._disabled("list_regions")

    def list_images(self) -> None:
        self._disabled("list_images")

    def list_ssh_keys(self) -> None:
        self._disabled("list_ssh_keys")

    def list_filesystems(self) -> None:
        self._disabled("list_filesystems")

    def list_instances(self) -> None:
        self._disabled("list_instances")

    def get_instance(self, instance_id: str) -> None:
        self._disabled(f"get_instance:{instance_id}")

    def get_quota(self) -> None:
        self._disabled("get_quota")

    def get_usage_estimate(self) -> None:
        self._disabled("get_usage_estimate")

    def launch_instance(self, *args: object, **kwargs: object) -> None:
        self._disabled("launch_instance")

    def terminate_instance(self, *args: object, **kwargs: object) -> None:
        self._disabled("terminate_instance")

    def restart_instance(self, *args: object, **kwargs: object) -> None:
        self._disabled("restart_instance")

    def create_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._disabled("create_ssh_key")

    def delete_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._disabled("delete_ssh_key")

    def create_filesystem(self, *args: object, **kwargs: object) -> None:
        self._disabled("create_filesystem")

    def delete_filesystem(self, *args: object, **kwargs: object) -> None:
        self._disabled("delete_filesystem")
