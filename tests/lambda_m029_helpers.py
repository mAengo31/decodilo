from __future__ import annotations

from pathlib import Path

from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.final_resource_lock import load_lambda_final_resource_lock
from decodilo.lambda_cloud.m029_launch_authorization import (
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
    arm_lambda_m029_from_package,
)
from decodilo.lambda_cloud.real_launch_client import LambdaM029RealLaunchClient
from decodilo.lambda_cloud.real_launch_executor import LambdaM029LaunchExecutor
from decodilo.lambda_cloud.real_launch_idempotency import build_m029_idempotency_report
from decodilo.lambda_cloud.real_launch_journal import LambdaM029LaunchJournal
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger
from decodilo.lambda_cloud.real_mutation_transport import (
    LambdaM029RealMutationTransport,
    LambdaM029TransportConfig,
)
from decodilo.lambda_cloud.real_terminate_client import LambdaM029RealTerminateClient
from decodilo.lambda_cloud.real_termination_executor import LambdaM029TerminationExecutor


def m029_fixture(tmp_path: Path):
    paths = write_m028_core_artifacts(tmp_path)
    authorization = load_lambda_m029_authorization_package(paths["m029_authorization"])
    resource = load_lambda_final_resource_lock(paths["resource"]).model_copy(
        update={"ssh_key_ref": "existing-test-ssh-key"}
    )
    idempotency = build_m029_idempotency_report(
        run_id="test-m029",
        plan_hash=authorization.launch_authorization.authorization_id,
    )
    arming = arm_lambda_m029_from_package(
        run_id="test-m029",
        execute_real_launch=True,
        confirm_billable_action=CONFIRM_BILLABLE_ACTION,
        confirm_terminate_required=CONFIRM_TERMINATE_REQUIRED,
        m028_report=paths["m028_report"],
        m029_authorization=paths["m029_authorization"],
        emergency_stop_present=True,
        idempotency_key=idempotency.launch_key.idempotency_key,
        fake_server_mode=True,
    )
    transport = LambdaM029RealMutationTransport(
        config=LambdaM029TransportConfig(
            base_url="memory://lambda-m029-test",
            fake_server_mode=True,
        )
    )
    journal = LambdaM029LaunchJournal(tmp_path / "journal.jsonl", run_id="test-m029")
    ledger = LambdaM029LaunchLedger(run_id="test-m029")
    return {
        **paths,
        "authorization": authorization,
        "resource": resource,
        "idempotency": idempotency,
        "arming": arming,
        "token": arming.token,
        "transport": transport,
        "journal": journal,
        "ledger": ledger,
        "launch_client": LambdaM029RealLaunchClient(transport),
        "terminate_client": LambdaM029RealTerminateClient(transport),
        "launch_executor": LambdaM029LaunchExecutor(
            client=LambdaM029RealLaunchClient(transport),
            journal=journal,
            ledger=ledger,
        ),
        "termination_executor": LambdaM029TerminationExecutor(
            client=LambdaM029RealTerminateClient(transport),
            journal=journal,
        ),
    }
