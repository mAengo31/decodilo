from __future__ import annotations

from pathlib import Path

from lambda_m023_helpers import write_text_evidence
from lambda_m024_helpers import write_m024_prepare_inputs

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    build_lambda_final_prelaunch_evidence_package,
    write_lambda_final_prelaunch_evidence_package,
)
from decodilo.lambda_cloud.final_prelaunch_review import (
    build_lambda_final_prelaunch_review,
    write_lambda_final_prelaunch_review,
)
from decodilo.lambda_cloud.first_launch_operator_checklist import (
    build_lambda_first_launch_operator_checklist,
    write_lambda_first_launch_operator_checklist,
)
from decodilo.lambda_cloud.first_launch_runbook import (
    build_lambda_first_launch_runbook,
    write_lambda_first_launch_runbook,
)
from decodilo.lambda_cloud.go_no_go_record import (
    build_lambda_go_no_go_record,
    write_lambda_go_no_go_record,
)
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    audit_lambda_real_mutation_skeleton,
    write_lambda_real_mutation_skeleton_audit_report,
)
from decodilo.lambda_cloud.semantic_mutation_audit import (
    audit_lambda_semantic_mutation_absence,
    write_lambda_semantic_mutation_audit_report,
)
from decodilo.lambda_cloud.termination_runbook import (
    build_lambda_termination_runbook,
    write_lambda_termination_runbook,
)


def write_m025_core_artifacts(tmp_path: Path) -> dict[str, Path]:
    m024 = write_m024_prepare_inputs(tmp_path)
    discovery = write_text_evidence(tmp_path, "m019c-discovery.json")
    audit = write_text_evidence(tmp_path, "m019c-audit.json")
    readiness = write_text_evidence(tmp_path, "m022-readiness.json")
    m023_package = write_text_evidence(tmp_path, "m023-evidence.json")
    skeleton = audit_lambda_real_mutation_skeleton(".")
    skeleton_path = tmp_path / "m024-skeleton.json"
    write_lambda_real_mutation_skeleton_audit_report(skeleton_path, skeleton)
    launch_runbook = build_lambda_first_launch_runbook()
    launch_runbook_path = tmp_path / "launch-runbook.json"
    write_lambda_first_launch_runbook(launch_runbook_path, launch_runbook)
    termination_runbook = build_lambda_termination_runbook()
    termination_runbook_path = tmp_path / "termination-runbook.json"
    write_lambda_termination_runbook(termination_runbook_path, termination_runbook)
    checklist = build_lambda_first_launch_operator_checklist(acknowledge_all=True)
    checklist_path = tmp_path / "checklist.json"
    write_lambda_first_launch_operator_checklist(checklist_path, checklist)
    semantic = audit_lambda_semantic_mutation_absence(".")
    semantic_path = tmp_path / "semantic.json"
    write_lambda_semantic_mutation_audit_report(semantic_path, semantic)
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=discovery,
        m019c_audit=audit,
        m020_report=m024["m020"],
        m022_readiness_package=readiness,
        m023_evidence_package=m023_package,
        m024_skeleton_audit=skeleton_path,
        m024_budget_lock=m024["budget"],
        m024_idempotency_plan=m024["idempotency"],
        m024_resource_scope=m024["scope"],
        m025_semantic_mutation_audit=semantic_path,
        m025_operator_checklist=checklist_path,
        m025_termination_runbook=termination_runbook_path,
        m025_launch_runbook=launch_runbook_path,
    )
    package_path = tmp_path / "final-evidence.json"
    write_lambda_final_prelaunch_evidence_package(package_path, package)
    review = build_lambda_final_prelaunch_review(
        evidence_package=package_path,
        operator_checklist=checklist_path,
        semantic_audit=semantic_path,
    )
    review_path = tmp_path / "review.json"
    write_lambda_final_prelaunch_review(review_path, review)
    go = build_lambda_go_no_go_record(review=review_path)
    go_path = tmp_path / "go-no-go.json"
    write_lambda_go_no_go_record(go_path, go)
    return {
        **m024,
        "discovery": discovery,
        "audit": audit,
        "readiness": readiness,
        "m023_package": m023_package,
        "skeleton": skeleton_path,
        "launch_runbook": launch_runbook_path,
        "termination_runbook": termination_runbook_path,
        "checklist": checklist_path,
        "semantic": semantic_path,
        "package": package_path,
        "review": review_path,
        "go": go_path,
    }
