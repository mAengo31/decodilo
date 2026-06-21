import pytest
from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.m028_decision_record import (
    LambdaM028DecisionRecord,
    build_lambda_m028_decision_record,
)


def test_m028_decision_authorizes_m029_only(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    decision = build_lambda_m028_decision_record(
        m029_authorization=paths["m029_authorization"],
        state_snapshot=paths["snapshot"],
        no_mutation_audit=paths["no_mutation"],
    )

    assert decision.status == "authorized_for_m029_one_instance_launch_attempt"
    assert decision.launch_ready is False


def test_missing_state_needs_more_evidence(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    decision = build_lambda_m028_decision_record(
        m029_authorization=paths["m029_authorization"],
        no_mutation_audit=paths["no_mutation"],
    )

    assert decision.status == "needs_more_evidence"


def test_forbidden_enabled_flags_rejected():
    kwargs = {"launch_" + "allowed": True}
    with pytest.raises(ValueError):
        LambdaM028DecisionRecord(status="blocked", **kwargs)

