from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.fake_server_launch_terminate_flow import (
    run_fake_server_launch_terminate_flow,
)
from decodilo.lambda_cloud.minimal_mutation_audit import audit_minimal_mutation_flow
from decodilo.lambda_cloud.minimal_mutation_preflight import (
    run_minimal_mutation_preflight,
)
from decodilo.lambda_cloud.minimal_mutation_report import LambdaMinimalMutationReport


def test_minimal_mutation_report_schema_flags_false():
    flow = run_fake_server_launch_terminate_flow(context=fake_context())
    audit = audit_minimal_mutation_flow(flow)
    preflight = run_minimal_mutation_preflight(context=fake_context(), audit_report=audit)

    report = LambdaMinimalMutationReport(preflight=preflight, fake_flow=flow, audit=audit)

    assert report.fake_server_execution_only is True
    assert report.real_lambda_api_used is False
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
