"""M029 owned-instance terminate client."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger
from decodilo.lambda_cloud.real_mutation_transport import LambdaM029RealMutationTransport


@dataclass
class LambdaM029RealTerminateClient:
    transport: LambdaM029RealMutationTransport

    def terminate_owned_instance(
        self,
        *,
        owned_instance_id: str,
        ledger: LambdaM029LaunchLedger,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
        failure_mode: str = "none",
    ) -> dict:
        if not ledger.can_terminate(owned_instance_id):
            raise ValueError("M029 termination blocked for unowned instance")
        return self.transport.request_json(
            operation="terminate_owned_instance",
            payload={"instance_ids": [owned_instance_id]},
            arming_token=arming_token,
            idempotency_key=idempotency_key,
            failure_mode=failure_mode,  # type: ignore[arg-type]
        )
