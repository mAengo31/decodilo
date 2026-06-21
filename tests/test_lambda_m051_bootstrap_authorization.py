from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.bootstrap_risk_review import (
    build_lambda_bootstrap_risk_review_from_paths,
    write_lambda_bootstrap_risk_review,
)
from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    build_lambda_m051_bootstrap_authorization_from_paths,
)


def test_m051_bootstrap_authorization_metadata_only_future_review(tmp_path):
    paths = write_m050_inputs(tmp_path)

    report = build_lambda_m051_bootstrap_authorization_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m051_metadata_only_bootstrap_review"
    )
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m051_bootstrap_authorization_blocks_missing_risk_review(tmp_path):
    paths = write_m050_inputs(tmp_path)
    risk = build_lambda_bootstrap_risk_review_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        evidence_schema=paths["evidence_schema"],
        lifecycle_closeout=None,
    )
    write_lambda_bootstrap_risk_review(paths["risk"], risk)

    report = build_lambda_m051_bootstrap_authorization_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
    )

    assert report.authorization_status == "not_authorized"
