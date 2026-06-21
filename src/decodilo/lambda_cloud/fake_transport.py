"""In-memory Lambda Cloud fake transport."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError, LambdaTransportError
from decodilo.lambda_cloud.fixtures import load_lambda_fixture_data
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard


class FakeLambdaTransportMetrics(BaseModel):
    model_config = ConfigDict(frozen=False)

    requests: int = 0
    read_requests: int = 0
    forbidden_mutations: int = 0
    throttles: int = 0
    server_errors: int = 0
    malformed_responses: int = 0
    simulated_latency_ticks: int = 0


class FakeLambdaTransport:
    """Fixture-backed local transport with deterministic failure modes."""

    def __init__(
        self,
        *,
        fixtures: dict[str, Any] | None = None,
        fixtures_dir: str | None = None,
        failure_mode: Literal["none", "throttle", "server_error", "malformed"] = "none",
        latency_ticks: int = 0,
        seed: int = 0,
    ) -> None:
        self.fixtures = deepcopy(fixtures) if fixtures is not None else load_lambda_fixture_data(
            fixtures_dir
        )
        self.failure_mode = failure_mode
        self.latency_ticks = max(0, latency_ticks)
        self.seed = seed
        self.metrics = FakeLambdaTransportMetrics()
        self._guard = LambdaMutationGuard()

    def request(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        self.metrics.requests += 1
        self.metrics.simulated_latency_ticks += self.latency_ticks
        report = self._guard.check(operation)
        if not report.allowed:
            if report.operation_type == "mutate":
                self.metrics.forbidden_mutations += 1
            raise LambdaMutationForbiddenError(report.reason)
        self.metrics.read_requests += 1
        if self.failure_mode == "throttle":
            self.metrics.throttles += 1
            raise LambdaTransportError("simulated Lambda 429 throttle")
        if self.failure_mode == "server_error":
            self.metrics.server_errors += 1
            raise LambdaTransportError("simulated Lambda 500 error")
        if self.failure_mode == "malformed":
            self.metrics.malformed_responses += 1
            return {"malformed": True}
        params = params or {}
        if operation == "list_instance_types":
            return deepcopy(self.fixtures["instance_types"])
        if operation == "list_regions":
            return deepcopy(self.fixtures["regions"])
        if operation == "list_images":
            return deepcopy(self.fixtures["images"])
        if operation == "list_ssh_keys":
            return deepcopy(self.fixtures["ssh_keys"])
        if operation == "list_filesystems":
            return deepcopy(self.fixtures["filesystems"])
        if operation == "list_instances":
            return deepcopy(self.fixtures["instances"])
        if operation == "get_instance":
            instance_id = str(params.get("instance_id", ""))
            for instance in self.fixtures["instances"]:
                if instance.get("instance_id") == instance_id:
                    return deepcopy(instance)
            raise LambdaTransportError(f"fake Lambda instance not found: {instance_id}")
        if operation == "get_quota":
            return deepcopy(self.fixtures["quota"])
        if operation == "get_usage_estimate":
            return deepcopy(self.fixtures["usage_estimate"])
        raise LambdaTransportError(f"unhandled fake Lambda operation: {operation}")
