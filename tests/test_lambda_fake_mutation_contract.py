from pathlib import Path

from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_mutation_contract import (
    evaluate_fake_lambda_mutation_contract,
)
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def _teardown_report(tmp_path):
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    launch = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    launch_path = tmp_path / "life" / "launch.json"
    launch_path.write_text(launch.to_json(), encoding="utf-8")
    return execute_fake_lambda_teardown(lifecycle_report_path=launch_path)


def test_valid_fake_lifecycle_passes_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path)

    contract = evaluate_fake_lambda_mutation_contract(report)

    assert contract.passed is True
    assert contract.fake_mutation_api_events_present is True
    assert contract.launch_allowed is False


def test_missing_idempotency_key_fails_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path).model_copy(update={"idempotency_summary": {}})

    contract = evaluate_fake_lambda_mutation_contract(report)

    assert contract.passed is False
    assert "idempotency key missing" in contract.errors[0]


def test_missing_journal_event_fails_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path).model_copy(
        update={"lifecycle_journal_ref": str(tmp_path / "missing.jsonl")}
    )

    contract = evaluate_fake_lambda_mutation_contract(report)

    assert contract.passed is False
    assert any("journal missing" in error for error in contract.errors)


def test_launch_allowed_true_fails_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path).model_copy(update={"launch_allowed": True})

    contract = evaluate_fake_lambda_mutation_contract(report)

    assert contract.passed is False
    assert any("launch flags false" in error for error in contract.errors)


def test_real_mutating_operations_fail_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path).model_copy(update={"real_mutating_operations": 1})

    contract = evaluate_fake_lambda_mutation_contract(report)

    assert contract.passed is False
    assert any("real Lambda API mutation" in error for error in contract.errors)


def test_real_looking_id_fails_contract(tmp_path) -> None:
    report = _teardown_report(tmp_path)
    resource = next(iter(report.lifecycle_state.resources.values()))
    bad_resource = resource.model_copy(update={"resource_id": "i-real"}, deep=True)
    state = report.lifecycle_state.model_copy(update={"resources": {"i-real": bad_resource}})
    bad_report = report.model_copy(update={"lifecycle_state": state})

    contract = evaluate_fake_lambda_mutation_contract(bad_report)

    assert contract.passed is False


def test_contract_report_serializes(tmp_path) -> None:
    report = _teardown_report(tmp_path)
    contract = evaluate_fake_lambda_mutation_contract(report)

    assert "fake_mutation_api_events_present" in contract.to_json()
    assert Path(report.lifecycle_journal_ref).exists()
