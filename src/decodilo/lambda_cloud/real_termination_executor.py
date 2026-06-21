"""M029 owned-instance termination executor."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_launch_journal import LambdaM029LaunchJournal
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger
from decodilo.lambda_cloud.real_launch_result import LambdaM029TerminationResult
from decodilo.lambda_cloud.real_mutation_transport import LambdaRealMutationTransportError
from decodilo.lambda_cloud.real_terminate_client import LambdaM029RealTerminateClient
from decodilo.lambda_cloud.real_termination_verifier import (
    verify_m029_owned_instance_terminated,
)


@dataclass
class LambdaM029TerminationExecutor:
    client: LambdaM029RealTerminateClient
    journal: LambdaM029LaunchJournal

    def terminate_owned_instance(
        self,
        *,
        owned_instance_id: str,
        ledger: LambdaM029LaunchLedger,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
        failure_mode: str = "none",
    ) -> tuple[LambdaM029TerminationResult, LambdaM029LaunchLedger]:
        if not ledger.can_terminate(owned_instance_id):
            raise ValueError("M029 executor refuses unowned termination")
        self.journal.append("m029_termination_request_about_to_send")
        try:
            self.journal.append("m029_termination_request_sent")
            payload = self.client.terminate_owned_instance(
                owned_instance_id=owned_instance_id,
                ledger=ledger,
                arming_token=arming_token,
                idempotency_key=idempotency_key,
                failure_mode=failure_mode,
            )
            response_received = True
        except TimeoutError:
            self.journal.append("m029_termination_response_timeout")
            payload = {}
            response_received = False
        except LambdaRealMutationTransportError as exc:
            self.journal.append("m029_termination_response_timeout")
            self.journal.append("m029_manual_review_required")
            return (
                LambdaM029TerminationResult(
                    request_sent=True,
                    response_received=_transport_status_was_received(self.client),
                    owned_instance_id=owned_instance_id,
                    idempotency_key=idempotency_key,
                    lifecycle_state="unknown",
                    termination_verified=False,
                    manual_review_required=True,
                    warnings=[
                        "termination transport error persisted for manual review",
                        "read-only verification required before any further action",
                    ],
                    errors=[str(exc)],
                ),
                ledger.model_copy(update={"manual_review_required": True}),
            )
        verification = verify_m029_owned_instance_terminated(
            transport=self.client.transport,
            arming_token=arming_token,
            owned_instance_id=owned_instance_id,
            idempotency_key=idempotency_key,
        )
        self.journal.append(
            "m029_readonly_verify_terminated",
            metadata={"termination_verified": verification.verification_passed},
        )
        new_ledger = ledger.record_terminated(
            terminate_attempt_id=idempotency_key,
            verified=verification.verification_passed,
        )
        if verification.manual_review_required:
            self.journal.append("m029_manual_review_required")
        else:
            self.journal.append("m029_termination_response_received")
        state = verification.observed_state
        if payload:
            instances = list((payload.get("data") or {}).get("terminated_instances") or [])
            if instances:
                state = str(instances[0].get("status") or state)
        return (
            LambdaM029TerminationResult(
                request_sent=True,
                response_received=response_received,
                owned_instance_id=owned_instance_id,
                idempotency_key=idempotency_key,
                lifecycle_state=state,
                termination_verified=verification.verification_passed,
                manual_review_required=verification.manual_review_required,
                warnings=verification.warnings,
                errors=verification.errors,
            ),
            new_ledger,
        )


def _transport_status_was_received(client: LambdaM029RealTerminateClient) -> bool:
    for item in reversed(client.transport.diagnostics_log):
        if item.operation != "terminate_owned_instance" or item.response_capture is None:
            continue
        return item.response_capture.metadata.status_code is not None
    return False
