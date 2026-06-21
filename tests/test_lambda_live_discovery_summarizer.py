from decodilo.lambda_cloud.api_models import LambdaInstance
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport
from decodilo.lambda_cloud.live_discovery_summarizer import summarize_lambda_live_discovery


def test_lambda_live_discovery_summary_redacts_public_ids() -> None:
    report = LambdaLiveDiscoveryReport(
        live_api_used=True,
        instances=[LambdaInstance(instance_id="i-summary", status="active", tags={})],
        unmanaged_instances=["i-summary"],
        endpoint_count_attempted=2,
        endpoint_count_succeeded=2,
    )

    summary = summarize_lambda_live_discovery(report, redaction_mode="public_summary")

    assert summary.unmanaged_count == 1
    assert summary.manual_review_required is True
    assert summary.unmanaged_instances != ["i-summary"]
    assert summary.launch_ready is False
    assert summary.launch_allowed is False
