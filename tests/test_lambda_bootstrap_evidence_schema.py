from decodilo.lambda_cloud.bootstrap_evidence_schema import (
    build_lambda_bootstrap_evidence_schema,
)


def test_bootstrap_evidence_schema_validates_bounds_and_redaction():
    report = build_lambda_bootstrap_evidence_schema()

    assert report.schema_valid is True
    assert report.secret_redaction_required is True
    assert report.raw_secret_storage_allowed is False
    assert "termination_verification" in report.required_evidence_fields
    assert report.command_output_max_bytes <= 16_384
    assert report.launch_ready is False
    assert report.launch_allowed is False
