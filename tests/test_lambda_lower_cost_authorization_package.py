from lambda_m037r_helpers import discovery, write_complete_package_inputs

from decodilo.lambda_cloud.lower_cost_authorization_package import (
    build_lambda_lower_cost_authorization_package,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    select_existing_lambda_ssh_key,
    write_lambda_existing_ssh_key_selection,
)


def test_complete_lower_cost_package_authorizes_future_review(tmp_path):
    paths = write_complete_package_inputs(tmp_path)
    report = build_lambda_lower_cost_authorization_package(
        launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        price_reconciliation=paths["price"],
        resource_reconciliation=paths["resource"],
        strand_compatibility=paths["strand"],
        response_loss_controls=paths["controls"],
    )

    assert (
        report.future_authorization_status
        == "authorized_for_future_lower_cost_launch_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_ssh_key_blocks_lower_cost_package(tmp_path):
    paths = write_complete_package_inputs(tmp_path)
    bad_ssh = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))
    write_lambda_existing_ssh_key_selection(paths["ssh"], bad_ssh)

    report = build_lambda_lower_cost_authorization_package(
        launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        price_reconciliation=paths["price"],
        resource_reconciliation=paths["resource"],
        strand_compatibility=paths["strand"],
        response_loss_controls=paths["controls"],
    )

    assert report.future_authorization_status == "not_authorized"
    assert "no existing SSH key names discovered or selected" in report.blockers
