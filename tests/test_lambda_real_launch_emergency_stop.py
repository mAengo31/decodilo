from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.real_launch_emergency_stop import (
    CONFIRM_EMERGENCY_TERMINATE,
    run_m029_emergency_stop,
)
from decodilo.lambda_cloud.real_launch_ledger import write_lambda_m029_launch_ledger


def test_real_launch_emergency_stop_owned_only(tmp_path):
    fx = m029_fixture(tmp_path)
    launch, ledger = fx["launch_executor"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )
    ledger_path = tmp_path / "ledger.json"
    write_lambda_m029_launch_ledger(ledger_path, ledger)

    report = run_m029_emergency_stop(
        journal_path=tmp_path / "journal.jsonl",
        ledger_path=ledger_path,
        terminate_client=fx["terminate_client"],
        executor=fx["termination_executor"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
        confirm_terminate_required=CONFIRM_EMERGENCY_TERMINATE,
    )

    assert report.emergency_stop_attempted is True
    assert report.owned_instance_id == launch.owned_instance_id
    assert report.termination_verified is True
