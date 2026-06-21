"""Fake Lambda mutation-shaped API client backed by local transport."""

from __future__ import annotations

from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaCreateFilesystemRequest,
    FakeLambdaCreateFilesystemResponse,
    FakeLambdaCreateSSHKeyRequest,
    FakeLambdaCreateSSHKeyResponse,
    FakeLambdaDeleteFilesystemRequest,
    FakeLambdaDeleteFilesystemResponse,
    FakeLambdaDeleteSSHKeyRequest,
    FakeLambdaDeleteSSHKeyResponse,
    FakeLambdaLaunchRequest,
    FakeLambdaLaunchResponse,
    FakeLambdaRestartRequest,
    FakeLambdaRestartResponse,
    FakeLambdaTerminateRequest,
    FakeLambdaTerminateResponse,
)
from decodilo.lambda_cloud.fake_mutation_transport import FakeLambdaMutationTransport


class FakeLambdaMutationAPI:
    def __init__(self, transport: FakeLambdaMutationTransport | None = None) -> None:
        self.transport = transport or FakeLambdaMutationTransport()

    def fake_launch_instance(
        self,
        request: FakeLambdaLaunchRequest,
    ) -> FakeLambdaLaunchResponse:
        return self.transport.launch_instance(request)

    def fake_terminate_instance(
        self,
        request: FakeLambdaTerminateRequest,
    ) -> FakeLambdaTerminateResponse:
        return self.transport.terminate_instance(request)

    def fake_restart_instance(
        self,
        request: FakeLambdaRestartRequest,
    ) -> FakeLambdaRestartResponse:
        return self.transport.restart_instance(request)

    def fake_create_ssh_key(
        self,
        request: FakeLambdaCreateSSHKeyRequest,
    ) -> FakeLambdaCreateSSHKeyResponse:
        return self.transport.create_ssh_key(request)

    def fake_delete_ssh_key(
        self,
        request: FakeLambdaDeleteSSHKeyRequest,
    ) -> FakeLambdaDeleteSSHKeyResponse:
        return self.transport.delete_ssh_key(request)

    def fake_create_filesystem(
        self,
        request: FakeLambdaCreateFilesystemRequest,
    ) -> FakeLambdaCreateFilesystemResponse:
        return self.transport.create_filesystem(request)

    def fake_delete_filesystem(
        self,
        request: FakeLambdaDeleteFilesystemRequest,
    ) -> FakeLambdaDeleteFilesystemResponse:
        return self.transport.delete_filesystem(request)
