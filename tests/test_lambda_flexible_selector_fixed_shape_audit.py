from lambda_m044g_helpers import write_m044g_inputs

from decodilo.lambda_cloud.flexible_selector_fixed_shape_audit import (
    load_lambda_flexible_selector_fixed_shape_audit,
)


def test_flexible_selector_fixed_shape_audit_passes_selector_path(tmp_path):
    paths = write_m044g_inputs(tmp_path)
    report = load_lambda_flexible_selector_fixed_shape_audit(paths["audit"])

    assert report.audit_passed is True
    assert report.selector_output_is_shape_source is True
    assert report.old_m028_m029_fixed_shape_fallback_blocked is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_flexible_selector_fixed_shape_audit_blocks_old_fallback(tmp_path):
    paths = write_m044g_inputs(tmp_path, risk_accepted=False)
    report = load_lambda_flexible_selector_fixed_shape_audit(paths["audit"])

    assert report.audit_passed is False
    assert "flexible_selector_authorization_not_ready" in report.blockers
