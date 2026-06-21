from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    build_lambda_m029_incident_report,
)
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    LambdaM029LaunchAuthorization,
)
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    build_lambda_m029_manual_console_confirmation,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report
from decodilo.lambda_cloud.m029_termination_authorization import (
    build_lambda_m029_termination_authorization,
)


def closed_m029_incident() -> LambdaM029IncidentReport:
    return build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(
            lambda_console_checked=True,
            no_instances_visible=True,
            no_pending_instances_visible=True,
            no_alert_instances_visible=True,
            no_owned_instance_found=True,
        ),
    )


def open_m029_incident() -> LambdaM029IncidentReport:
    return build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(),
    )


def prior_m029_report() -> LambdaM029Report:
    return ambiguous_m029_report()


def m029_authorization_package() -> LambdaM029AuthorizationPackage:
    launch = LambdaM029LaunchAuthorization(
        authorization_id="lambda-m029-launch-test",
        authorized_operations=[
            "launch_one_instance",
            "read_only_verify_instance",
            "terminate_owned_instance",
            "read_only_verify_terminated",
        ],
        forbidden_operations=["restart", "create/delete SSH key"],
        planned_instance_type="gpu_8x_h100_sxm",
        planned_region="us-west-1",
        image_ref="image-review-only",
        idempotency_plan_hash="idempotency-hash",
        budget_lock_hash="budget-hash",
        resource_lock_hash="resource-hash",
        launch_window_lock_hash="window-hash",
        teardown_plan_hash="teardown-hash",
        operator_confirmation_hash="operator-hash",
    )
    return LambdaM029AuthorizationPackage(
        launch_authorization=launch,
        termination_authorization=build_lambda_m029_termination_authorization(),
        package_passed=True,
    )
