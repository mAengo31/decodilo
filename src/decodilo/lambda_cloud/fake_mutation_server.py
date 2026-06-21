"""Local fake mutation server facade without real networking."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from decodilo.lambda_cloud.fake_mutation_api import FakeLambdaMutationAPI
from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchRequest,
    FakeLambdaTerminateRequest,
)
from decodilo.lambda_cloud.fake_mutation_responses import (
    FakeLambdaMutationAPIEnvelope,
    success_envelope,
)


class FakeLambdaMutationServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    host: str = "127.0.0.1"
    fake_mode: bool = True

    def validate_local(self) -> None:
        if self.host != "127.0.0.1":
            raise ValueError("fake mutation server may bind only to 127.0.0.1")
        if not self.fake_mode:
            raise ValueError("fake mutation server requires fake_mode=true")


class FakeLambdaMutationServer:
    def __init__(self, config: FakeLambdaMutationServerConfig | None = None) -> None:
        self.config = config or FakeLambdaMutationServerConfig()
        self.config.validate_local()
        self.api = FakeLambdaMutationAPI()

    def handle_launch(self, request: FakeLambdaLaunchRequest) -> FakeLambdaMutationAPIEnvelope:
        return success_envelope(
            "fake_launch_instance",
            self.api.fake_launch_instance(request),
        )

    def handle_terminate(
        self,
        request: FakeLambdaTerminateRequest,
    ) -> FakeLambdaMutationAPIEnvelope:
        return success_envelope(
            "fake_terminate_instance",
            self.api.fake_terminate_instance(request),
        )
