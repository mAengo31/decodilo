"""Local fake Lambda API server facade.

This intentionally does not open sockets. It provides server-like dispatch for
tests while retaining a localhost-only binding contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport


class FakeLambdaServerInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    host: str
    bound_to_localhost_only: bool
    live_api_used: bool = False


class FakeLambdaAPIServer:
    """In-process fake server. No network listener is created."""

    def __init__(self, *, host: str = "127.0.0.1", transport: FakeLambdaTransport | None = None):
        if host not in {"127.0.0.1", "localhost"}:
            raise ValueError("fake Lambda server may only bind to localhost")
        self.host = host
        self.transport = transport or FakeLambdaTransport()

    def info(self) -> FakeLambdaServerInfo:
        return FakeLambdaServerInfo(host=self.host, bound_to_localhost_only=True)

    def handle(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        return self.transport.request(operation, params)
