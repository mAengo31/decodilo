"""M029 launch client for exactly one instance."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.lambda_cloud.final_resource_lock import LambdaFinalResourceLock
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_mutation_transport import LambdaM029RealMutationTransport


@dataclass
class LambdaM029RealLaunchClient:
    transport: LambdaM029RealMutationTransport

    def launch_one_instance(
        self,
        *,
        resource_lock: LambdaFinalResourceLock,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
        failure_mode: str = "none",
    ) -> dict:
        if not resource_lock.ssh_key_ref:
            raise ValueError("M036R Strand-compatible launch requires an existing SSH key name")
        if resource_lock.filesystem_refs:
            raise ValueError("M029 first launch forbids filesystem attachment")
        payload = {
            "region_name": resource_lock.planned_region,
            "instance_type_name": resource_lock.planned_instance_type,
            "ssh_key_names": [resource_lock.ssh_key_ref],
            "quantity": 1,
        }
        if resource_lock.filesystem_refs:
            payload["file_system_names"] = resource_lock.filesystem_refs
        return self.transport.request_json(
            operation="launch_one_instance",
            payload=payload,
            arming_token=arming_token,
            idempotency_key=idempotency_key,
            failure_mode=failure_mode,  # type: ignore[arg-type]
        )
