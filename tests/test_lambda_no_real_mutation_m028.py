from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    build_fake_server_execution_context,
)
from decodilo.lambda_cloud.semantic_mutation_audit import audit_lambda_semantic_mutation_absence


def test_m028_does_not_enable_real_lambda_minimal_mutation_path():
    live_url = "https://" + "cloud.lambdalabs.com" + "/api/v1"

    try:
        build_fake_server_execution_context(base_url=live_url)
    except ValueError as exc:
        assert "real Lambda" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("real Lambda URL should be rejected")


def test_semantic_audit_still_passes_current_project():
    audit = audit_lambda_semantic_mutation_absence(".")

    assert audit.passed is True
    assert audit.launch_allowed is False

