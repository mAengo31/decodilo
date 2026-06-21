"""M029 launch executor for one owned Lambda instance."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.lambda_cloud.final_resource_lock import LambdaFinalResourceLock
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_launch_client import LambdaM029RealLaunchClient
from decodilo.lambda_cloud.real_launch_journal import LambdaM029LaunchJournal
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger
from decodilo.lambda_cloud.real_launch_result import LambdaM029LaunchResult
from decodilo.lambda_cloud.real_mutation_transport import LambdaRealMutationTransportError


@dataclass
class LambdaM029LaunchExecutor:
    client: LambdaM029RealLaunchClient
    journal: LambdaM029LaunchJournal
    ledger: LambdaM029LaunchLedger

    def launch_one_instance(
        self,
        *,
        resource_lock: LambdaFinalResourceLock,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
        failure_mode: str = "none",
    ) -> tuple[LambdaM029LaunchResult, LambdaM029LaunchLedger]:
        self.journal.append("m029_launch_request_about_to_send")
        try:
            self.journal.append("m029_launch_request_sent")
            payload = self.client.launch_one_instance(
                resource_lock=resource_lock,
                arming_token=arming_token,
                idempotency_key=idempotency_key,
                failure_mode=failure_mode,
            )
        except TimeoutError:
            self.journal.append("m029_launch_response_timeout")
            reconciled_id = _reconcile_fake_created_instance(self.client, idempotency_key)
            if reconciled_id:
                ledger = self.ledger.record_owned(
                    reconciled_id,
                    launch_attempt_id=idempotency_key,
                )
                self.journal.append(
                    "m029_owned_instance_recorded",
                    metadata={"owned_instance_id": reconciled_id},
                )
                return (
                    LambdaM029LaunchResult(
                        request_sent=True,
                        response_received=False,
                        owned_instance_id=reconciled_id,
                        idempotency_key=idempotency_key,
                        lifecycle_state="running",
                        manual_review_required=False,
                        warnings=["launch response lost; owned instance reconciled read-only"],
                    ),
                    ledger,
                )
            self.journal.append("m029_manual_review_required")
            return (
                LambdaM029LaunchResult(
                    request_sent=True,
                    response_received=False,
                    idempotency_key=idempotency_key,
                    manual_review_required=True,
                    warnings=["launch response lost and ownership could not be reconciled"],
                ),
                self.ledger.model_copy(update={"manual_review_required": True}),
            )
        except LambdaRealMutationTransportError as exc:
            response_received = _transport_status_was_received(self.client)
            if response_received:
                self.journal.append("m029_launch_response_received")
            else:
                self.journal.append("m029_launch_response_timeout")
            self.journal.append("m029_manual_review_required")
            return (
                LambdaM029LaunchResult(
                    request_sent=True,
                    response_received=response_received,
                    idempotency_key=idempotency_key,
                    manual_review_required=True,
                    errors=[str(exc)],
                    warnings=[
                        "launch transport error persisted for manual review",
                        "automatic launch retry is forbidden",
                    ],
                ),
                self.ledger.model_copy(update={"manual_review_required": True}),
            )
        instance_ids = list((payload.get("data") or {}).get("instance_ids") or [])
        if len(instance_ids) != 1:
            self.journal.append("m029_manual_review_required")
            return (
                LambdaM029LaunchResult(
                    request_sent=True,
                    response_received=True,
                    idempotency_key=idempotency_key,
                    manual_review_required=True,
                    errors=["launch response did not contain exactly one instance id"],
                ),
                self.ledger.model_copy(update={"manual_review_required": True}),
            )
        owned_id = str(instance_ids[0])
        if owned_id.startswith("malformed"):
            self.journal.append("m029_manual_review_required")
            return (
                LambdaM029LaunchResult(
                    request_sent=True,
                    response_received=True,
                    idempotency_key=idempotency_key,
                    owned_instance_id=owned_id,
                    manual_review_required=True,
                    errors=["launch response contained malformed instance id"],
                ),
                self.ledger.model_copy(update={"manual_review_required": True}),
            )
        ledger = self.ledger.record_owned(owned_id, launch_attempt_id=idempotency_key)
        self.journal.append("m029_launch_response_received")
        self.journal.append(
            "m029_owned_instance_recorded",
            metadata={"owned_instance_id": owned_id},
        )
        self.journal.append(
            "m029_readonly_verify_running",
            metadata={"owned_instance_id": owned_id},
        )
        return (
            LambdaM029LaunchResult(
                request_sent=True,
                response_received=True,
                owned_instance_id=owned_id,
                idempotency_key=idempotency_key,
                lifecycle_state="running",
            ),
            ledger,
        )


def _reconcile_fake_created_instance(
    client: LambdaM029RealLaunchClient,
    idempotency_key: str,
) -> str | None:
    registry = client.transport.fake_registry
    instance_id = registry.launch_by_key.get(idempotency_key)
    return instance_id if instance_id in registry.resources else None


def _transport_status_was_received(client: LambdaM029RealLaunchClient) -> bool:
    for item in reversed(client.transport.diagnostics_log):
        if item.operation != "launch_one_instance" or item.response_capture is None:
            continue
        return item.response_capture.metadata.status_code is not None
    return False
