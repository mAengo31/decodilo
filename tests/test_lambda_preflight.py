from decodilo.lambda_cloud.credential_model import LambdaAPIKeyRef, LambdaCredentialPolicy
from decodilo.lambda_cloud.discovery import discover_lambda_from_client
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport
from decodilo.lambda_cloud.live_resource_ledger import LambdaLiveResourceLedgerReport
from decodilo.lambda_cloud.preflight import run_lambda_preflight
from decodilo.lambda_cloud.read_only_audit import (
    LambdaReadOnlyAuditEntry,
    audit_lambda_read_only,
)
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.resource_ledger import build_lambda_resource_ledger
from decodilo.lambda_cloud.teardown_plan import build_lambda_teardown_plan


def test_lambda_preflight_passes_fake_readiness_but_non_launchable() -> None:
    discovery = discover_lambda_from_client(ReadOnlyLambdaCloudClient(FakeLambdaTransport()))
    launch = build_lambda_launch_plan(
        run_id="run-1",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )
    teardown = build_lambda_teardown_plan(
        run_id=launch.run_id,
        planned_node_ids=[node.node_id for node in launch.nodes],
    )
    ledger = build_lambda_resource_ledger(
        run_id=launch.run_id,
        planned_node_ids=[node.node_id for node in launch.nodes],
        discovery=discovery,
    )
    credentials = LambdaCredentialPolicy(
        api_key_refs=[
            LambdaAPIKeyRef(
                key_name="future-readonly",
                purpose="future discovery",
                required_scope="read_only",
            )
        ]
    )

    report = run_lambda_preflight(
        launch_plan=launch,
        teardown_plan=teardown,
        ledger=ledger,
        discovery_report=discovery,
        credential_policy=credentials,
    )

    assert report.passed
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.mutation_guard["launch_instance"]["allowed"] is False


def test_lambda_preflight_fails_missing_teardown() -> None:
    report = run_lambda_preflight()

    assert not report.passed
    assert "missing Lambda teardown plan" in report.errors


def test_lambda_preflight_accepts_live_style_read_only_evidence() -> None:
    launch = build_lambda_launch_plan(
        run_id="run-1",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )
    teardown = build_lambda_teardown_plan(
        run_id=launch.run_id,
        planned_node_ids=[node.node_id for node in launch.nodes],
    )
    audit = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="list_instances",
                method="GET",
                endpoint="/instances",
                allowed=True,
                status_code=200,
                live_api_used=True,
            )
        ]
    )
    discovery = LambdaLiveDiscoveryReport(live_api_used=True, audit_log=audit.entries)
    ledger = LambdaLiveResourceLedgerReport(
        run_id=launch.run_id,
        discovered_count=0,
        planned_count=1,
        matched_count=0,
        unmanaged_count=0,
        live_api_used=True,
    )

    report = run_lambda_preflight(
        launch_plan=launch,
        teardown_plan=teardown,
        live_discovery_report=discovery,
        read_only_audit=audit,
        live_ledger=ledger,
    )

    assert report.passed
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.read_only_audit_summary["read_operations"] == 1


def test_lambda_preflight_fails_mutating_audit_entry() -> None:
    discovery = LambdaLiveDiscoveryReport(live_api_used=True)
    audit = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="launch_instance",
                method="POST",
                endpoint="/instances",
                allowed=True,
                status_code=200,
                live_api_used=True,
                mutation=True,
            )
        ]
    )

    report = run_lambda_preflight(
        live_discovery_report=discovery,
        read_only_audit=audit,
    )

    assert not report.passed
    assert any("mutating operation" in error for error in report.errors)


def test_lambda_preflight_allows_optional_unsupported_endpoint_warnings() -> None:
    launch = build_lambda_launch_plan(
        run_id="run-optional",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )
    teardown = build_lambda_teardown_plan(
        run_id=launch.run_id,
        planned_node_ids=[node.node_id for node in launch.nodes],
    )
    audit = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="get_quota",
                method="GET",
                endpoint="/quota",
                allowed=True,
                status_code=404,
                live_api_used=True,
                error="404",
            )
        ]
    )
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        audit_log=audit.entries,
        endpoint_count_failed_optional=1,
        endpoint_count_unsupported_optional=1,
        required_endpoint_success=True,
    )
    ledger = LambdaLiveResourceLedgerReport(
        run_id=launch.run_id,
        discovered_count=0,
        planned_count=1,
        matched_count=0,
        unmanaged_count=0,
        live_api_used=True,
    )

    report = run_lambda_preflight(
        launch_plan=launch,
        teardown_plan=teardown,
        live_discovery_report=discovery,
        read_only_audit=audit,
        live_ledger=ledger,
    )

    assert report.passed
    assert report.preflight_status == "passed_read_only_with_warnings"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lambda_preflight_fails_required_endpoint_failure() -> None:
    audit = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="list_instances",
                method="GET",
                endpoint="/instances",
                allowed=True,
                status_code=500,
                live_api_used=True,
                error="500",
            )
        ]
    )
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        audit_log=audit.entries,
        endpoint_count_failed_required=1,
        required_endpoint_success=False,
    )

    report = run_lambda_preflight(
        live_discovery_report=discovery,
        read_only_audit=audit,
    )

    assert not report.passed
    assert any("required endpoints" in error for error in report.errors)
