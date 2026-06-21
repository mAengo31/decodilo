from decodilo.lambda_cloud.discovery import discover_lambda_from_client
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.resource_ledger import build_lambda_resource_ledger


def test_lambda_resource_ledger_flags_unmanaged_fake_instance() -> None:
    discovery = discover_lambda_from_client(
        ReadOnlyLambdaCloudClient(FakeLambdaTransport(fixtures_dir="tests/fixtures/lambda_cloud"))
    )

    report = build_lambda_resource_ledger(
        run_id="run-1",
        planned_node_ids=["node-0"],
        discovery=discovery,
    )

    assert report.planned_count == 1
    assert report.unmanaged_count == 1
    assert "i-fixture-unmanaged" in report.orphan_candidates
    assert not report.ledger.launch_performed
    assert not report.ledger.terminate_performed
