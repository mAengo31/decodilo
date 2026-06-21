from decodilo.lambda_cloud.api_models import LambdaUsageEstimate
from decodilo.lambda_cloud.billing_model import estimate_lambda_billing


def test_lambda_billing_estimate_uses_manual_fixture_data() -> None:
    usage = LambdaUsageEstimate(estimated_hourly_cost=1.5, running_instance_count=2)

    estimate = estimate_lambda_billing(
        hourly_price=10.0,
        node_count=2,
        planned_hours=3.0,
        usage_estimate=usage,
    )

    assert estimate.estimated_hourly_cost == 20.0
    assert estimate.estimated_total_cost == 60.0
    assert estimate.live_billing_used is False
