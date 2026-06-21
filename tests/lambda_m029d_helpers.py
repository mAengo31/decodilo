from decodilo.lambda_cloud.m029_report import LambdaM029Report


def ambiguous_m029_report() -> LambdaM029Report:
    return LambdaM029Report(
        run_id="run",
        real_lambda_api_used=True,
        launch_request_sent=True,
        launch_response_received=False,
        termination_request_sent=False,
        termination_response_received=False,
        termination_verified=False,
        manual_review_required=True,
        mutating_operations=1,
        billable_action_performed=True,
        estimated_spend=0.01,
        elapsed_seconds=0.3,
    )
