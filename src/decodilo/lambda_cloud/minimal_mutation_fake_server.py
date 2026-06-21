"""Fake-local minimal Lambda mutation server facade."""

from __future__ import annotations

from dataclasses import dataclass, field

from decodilo.lambda_cloud.fake_server_resource_registry import (
    LambdaFakeServerResourceRegistry,
)
from decodilo.lambda_cloud.minimal_mutation_fake_transport import (
    LambdaMinimalMutationFakeTransport,
)
from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
)


@dataclass
class LambdaMinimalMutationFakeServer:
    registry: LambdaFakeServerResourceRegistry = field(
        default_factory=LambdaFakeServerResourceRegistry
    )
    bind_host: str = "127.0.0.1"
    base_url: str = "memory://lambda-minimal-fake-server"

    def __post_init__(self) -> None:
        if self.bind_host not in {"127.0.0.1", "localhost"}:
            raise ValueError("M027 fake server may bind only to localhost")
        if "lambdalabs.com" in self.base_url.lower() or "lambda.ai" in self.base_url.lower():
            raise ValueError("M027 fake server rejects real Lambda base URLs")

    def transport(self) -> LambdaMinimalMutationFakeTransport:
        return LambdaMinimalMutationFakeTransport(registry=self.registry, base_url=self.base_url)

    def launch_one_instance(self, request: LambdaMinimalLaunchOneInstanceRequest) -> dict:
        return self.transport().launch_one_instance(request)

    def terminate_owned_instance(
        self,
        request: LambdaMinimalTerminateOwnedInstanceRequest,
    ) -> dict:
        return self.transport().terminate_owned_instance(request)
