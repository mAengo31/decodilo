from decodilo.storage.remote_backend_risk_register import (
    RemoteBackendRisk,
    RemoteBackendRiskMitigation,
    build_default_remote_backend_risk_register,
    update_remote_backend_risk_register,
)


def test_default_register_contains_required_blocking_risks() -> None:
    register = build_default_remote_backend_risk_register(proposal_ref="proposal.json")
    risk_ids = {risk.risk_id for risk in register.risks}

    assert "credential_leakage" in risk_ids
    assert "gc_deletes_live_artifact" in risk_ids
    assert "credential_leakage" in register.blockers
    assert register.remote_backend_enabled is False


def test_mitigated_critical_risk_no_longer_blocks() -> None:
    risk = RemoteBackendRisk(
        risk_id="credential_leakage",
        category="credential",
        severity="critical",
        likelihood="medium",
        description="credential leakage",
        mitigation=RemoteBackendRiskMitigation(
            description="mitigated",
            evidence_refs=["evidence.json"],
        ),
        status="mitigated",
        blocks_sdk_addition=True,
    )
    register = update_remote_backend_risk_register(proposal_ref=None, risks=[risk])

    assert register.blockers == []
    assert register.model_validate_json(register.to_json()) == register
