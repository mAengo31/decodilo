from lambda_m037r_helpers import discovery
from lambda_m040_helpers import (
    capacity_closeout,
    m039_capacity_report,
    spend_audit,
    transport_error,
)

from decodilo.lambda_cloud.capacity_error_closeout import (
    build_lambda_capacity_error_closeout,
)


def test_capacity_error_zero_discovery_closes_no_instance_created():
    report = capacity_closeout()

    assert report.closeout_status == "closed_capacity_unavailable_no_instance_created"
    assert report.closeout_succeeded is True
    assert report.capacity_error_confirmed is True
    assert report.termination_required is False
    assert report.future_launch_blocked_for_same_shape is True
    assert report.future_availability_first_required is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_error_with_discovered_instance_is_unresolved():
    report = build_lambda_capacity_error_closeout(
        m039_report=m039_capacity_report(),
        transport_error=transport_error(),
        post_discovery=discovery(unmanaged=("i-visible",)),
        spend_audit=spend_audit(),
    )

    assert report.closeout_status == "unresolved"
    assert "post_discovery_found_visible_or_unmanaged_instances" in report.blockers


def test_missing_provider_error_message_is_unresolved():
    launch_report = m039_capacity_report().model_copy(
        update={"launch_response_error_message_redacted": None}
    )
    report = build_lambda_capacity_error_closeout(
        m039_report=launch_report,
        transport_error=None,
        post_discovery=discovery(),
        spend_audit=spend_audit(),
    )

    assert report.closeout_status == "unresolved"
    assert "capacity_error_message_missing_or_unrecognized" in report.blockers
