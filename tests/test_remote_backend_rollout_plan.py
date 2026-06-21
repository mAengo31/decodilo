from decodilo.storage.remote_backend_rollout_plan import build_remote_backend_rollout_plan


def test_rollout_plan_defines_future_phases_but_enables_none() -> None:
    plan = build_remote_backend_rollout_plan(proposal_ref="proposal.json")

    phase0 = next(phase for phase in plan.phases if phase.phase_id == "phase_0_design_only")
    assert "add SDK" in phase0.forbidden_operations
    assert phase0.current_phase is True
    assert all(phase.remote_backend_enabled is False for phase in plan.phases)
    assert all(phase.manual_approval_required is True for phase in plan.phases)
    assert plan.remote_backend_enabled is False
    assert plan.model_validate_json(plan.to_json()) == plan
