from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.first_launch_evidence_package import (
    build_lambda_first_launch_evidence_package,
)
from decodilo.lambda_cloud.first_launch_failure_modes import (
    build_lambda_first_launch_failure_mode_table,
    write_lambda_first_launch_failure_mode_table,
)
from decodilo.lambda_cloud.first_launch_safety_case import (
    build_lambda_first_launch_safety_case,
    write_lambda_first_launch_safety_case,
)
from decodilo.lambda_cloud.real_mutation_absence_audit import (
    audit_real_lambda_mutation_absence,
    write_real_lambda_mutation_absence_audit_report,
)
from decodilo.lambda_cloud.real_mutation_arming_gate import (
    build_lambda_real_mutation_arming_gate_design,
    write_lambda_real_mutation_arming_gate_design,
)
from decodilo.lambda_cloud.real_mutation_boundary_proposal import (
    build_lambda_real_mutation_boundary_proposal,
    write_lambda_real_mutation_boundary_proposal,
)
from decodilo.lambda_cloud.real_mutation_kill_switch_design import (
    build_lambda_kill_switch_design,
    write_lambda_kill_switch_design,
)
from decodilo.lambda_cloud.real_mutation_operation_spec import (
    build_lambda_real_mutation_operation_set,
    write_lambda_real_mutation_operation_set,
)
from decodilo.lambda_cloud.termination_verification_policy import (
    build_lambda_termination_verification_policy,
    write_lambda_termination_verification_policy,
)


def write_text_evidence(tmp_path: Path, name: str, payload: str = "{}\n") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def write_m023_core_artifacts(tmp_path: Path) -> dict[str, Path]:
    discovery = write_text_evidence(tmp_path, "m019c-discovery.json")
    audit = write_text_evidence(tmp_path, "m019c-audit.json")
    preflight = write_text_evidence(tmp_path, "m019c-preflight.json")
    m020 = write_text_evidence(tmp_path, "m020.json")
    m021 = write_text_evidence(tmp_path, "m021-lifecycle.json")
    stress = write_text_evidence(tmp_path, "m022-stress.json")
    teardown_audit = write_text_evidence(tmp_path, "m022-teardown-audit.json")
    readiness = write_text_evidence(tmp_path, "m022-readiness.json")
    absence = audit_real_lambda_mutation_absence(".")
    absence_path = tmp_path / "m022-absence.json"
    write_real_lambda_mutation_absence_audit_report(absence_path, absence)
    operation = build_lambda_real_mutation_operation_set()
    operation_path = tmp_path / "operation.json"
    write_lambda_real_mutation_operation_set(operation_path, operation)
    arming = build_lambda_real_mutation_arming_gate_design()
    arming_path = tmp_path / "arming.json"
    write_lambda_real_mutation_arming_gate_design(arming_path, arming)
    kill_switch = build_lambda_kill_switch_design()
    kill_switch_path = tmp_path / "kill-switch.json"
    write_lambda_kill_switch_design(kill_switch_path, kill_switch)
    termination = build_lambda_termination_verification_policy()
    termination_path = tmp_path / "termination-policy.json"
    write_lambda_termination_verification_policy(termination_path, termination)
    failure_modes = build_lambda_first_launch_failure_mode_table()
    failure_modes_path = tmp_path / "failure-modes.json"
    write_lambda_first_launch_failure_mode_table(failure_modes_path, failure_modes)
    proposal = build_lambda_real_mutation_boundary_proposal(
        m019c_discovery=discovery,
        m020_report=m020,
        m022_readiness_package=readiness,
        real_mutation_absence_audit=absence_path,
    )
    proposal_path = tmp_path / "proposal.json"
    write_lambda_real_mutation_boundary_proposal(proposal_path, proposal)
    safety = build_lambda_first_launch_safety_case(
        proposal_ref=proposal_path,
        operation_spec=operation_path,
        fake_lifecycle_evidence_ref=readiness,
        termination_policy=termination,
    )
    safety_path = tmp_path / "safety.json"
    write_lambda_first_launch_safety_case(safety_path, safety)
    return {
        "discovery": discovery,
        "audit": audit,
        "preflight": preflight,
        "m020": m020,
        "m021": m021,
        "stress": stress,
        "teardown_audit": teardown_audit,
        "readiness": readiness,
        "absence": absence_path,
        "operation": operation_path,
        "arming": arming_path,
        "kill_switch": kill_switch_path,
        "termination": termination_path,
        "failure_modes": failure_modes_path,
        "proposal": proposal_path,
        "safety": safety_path,
    }


def build_m023_evidence_package_from_refs(refs: dict[str, Path], **updates):
    args = {
        "m019c_discovery": refs["discovery"],
        "m019c_audit": refs["audit"],
        "m019c_preflight": refs["preflight"],
        "m020_report": refs["m020"],
        "m021_fake_lifecycle_report": refs["m021"],
        "m022_stress_report": refs["stress"],
        "m022_teardown_audit": refs["teardown_audit"],
        "m022_real_mutation_absence_audit": refs["absence"],
        "m022_readiness_package": refs["readiness"],
        "proposal": refs["proposal"],
        "operation_spec": refs["operation"],
        "arming_gate": refs["arming"],
        "kill_switch": refs["kill_switch"],
        "termination_policy": refs["termination"],
        "safety_case": refs["safety"],
        "failure_modes": refs["failure_modes"],
    }
    args.update(updates)
    return build_lambda_first_launch_evidence_package(**args)
