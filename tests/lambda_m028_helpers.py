from __future__ import annotations

from pathlib import Path

from lambda_m027_helpers import write_m027_core_artifacts

from decodilo.lambda_cloud.final_budget_lock import (
    build_lambda_final_budget_lock,
    write_lambda_final_budget_lock,
)
from decodilo.lambda_cloud.final_no_mutation_audit import (
    LambdaFinalNoMutationAudit,
    write_lambda_final_no_mutation_audit,
)
from decodilo.lambda_cloud.final_operator_confirmation import (
    build_lambda_final_operator_confirmation_template,
    write_lambda_final_operator_confirmation,
)
from decodilo.lambda_cloud.final_prelaunch_state_snapshot import (
    build_lambda_final_prelaunch_state_snapshot,
    write_lambda_final_prelaunch_state_snapshot,
)
from decodilo.lambda_cloud.final_resource_lock import (
    build_lambda_final_resource_lock,
    write_lambda_final_resource_lock,
)
from decodilo.lambda_cloud.final_teardown_verification_plan import (
    build_lambda_final_teardown_verification_plan,
    write_lambda_final_teardown_verification_plan,
)
from decodilo.lambda_cloud.launch_window_lock import (
    build_lambda_launch_window_lock,
    write_lambda_launch_window_lock,
)
from decodilo.lambda_cloud.m020_report import load_lambda_m020_report
from decodilo.lambda_cloud.m028_decision_record import (
    build_lambda_m028_decision_record,
    write_lambda_m028_decision_record,
)
from decodilo.lambda_cloud.m028_report import build_lambda_m028_report, write_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    build_lambda_m029_authorization_package,
    write_lambda_m029_authorization_package,
)


def clean_no_mutation_audit() -> LambdaFinalNoMutationAudit:
    return LambdaFinalNoMutationAudit(
        no_real_mutation_path_detected=True,
        no_real_post_put_patch_delete_detected=True,
        live_client_read_only=True,
        fake_only_paths_labeled=True,
        launch_flags_false=True,
        billable_action_false=True,
        audit_passed=True,
    )


def write_m028_core_artifacts(tmp_path: Path) -> dict[str, Path]:
    paths = write_m027_core_artifacts(tmp_path)
    m020 = load_lambda_m020_report(paths["m020"])
    valid_discovery_path = Path(m020.discovery_report_ref)

    snapshot = build_lambda_final_prelaunch_state_snapshot(
        discovery_report=valid_discovery_path,
        m020_report=paths["m020"],
    )
    snapshot_path = tmp_path / "m028-state-snapshot.json"
    write_lambda_final_prelaunch_state_snapshot(snapshot_path, snapshot)

    budget = build_lambda_final_budget_lock(paths["m020"])
    budget_path = tmp_path / "m028-budget-lock.json"
    write_lambda_final_budget_lock(budget_path, budget)

    resource = build_lambda_final_resource_lock(paths["m020"])
    resource_path = tmp_path / "m028-resource-lock.json"
    write_lambda_final_resource_lock(resource_path, resource)

    window = build_lambda_launch_window_lock()
    window_path = tmp_path / "m028-launch-window-lock.json"
    write_lambda_launch_window_lock(window_path, window)

    teardown = build_lambda_final_teardown_verification_plan()
    teardown_path = tmp_path / "m028-teardown-verification-plan.json"
    write_lambda_final_teardown_verification_plan(teardown_path, teardown)

    operator = build_lambda_final_operator_confirmation_template(acknowledge_all=True)
    operator_path = tmp_path / "m028-operator-confirmation.json"
    write_lambda_final_operator_confirmation(operator_path, operator)

    no_mutation = clean_no_mutation_audit()
    no_mutation_path = tmp_path / "m028-no-mutation-audit.json"
    write_lambda_final_no_mutation_audit(no_mutation_path, no_mutation)

    authorization = build_lambda_m029_authorization_package(
        state_snapshot=snapshot_path,
        budget_lock=budget_path,
        resource_lock=resource_path,
        launch_window_lock=window_path,
        teardown_plan=teardown_path,
        operator_confirmation=operator_path,
        no_mutation_audit=no_mutation_path,
    )
    authorization_path = tmp_path / "m029-authorization.json"
    write_lambda_m029_authorization_package(authorization_path, authorization)

    decision = build_lambda_m028_decision_record(
        m029_authorization=authorization_path,
        state_snapshot=snapshot_path,
        no_mutation_audit=no_mutation_path,
    )
    decision_path = tmp_path / "m028-decision.json"
    write_lambda_m028_decision_record(decision_path, decision)

    report = build_lambda_m028_report(
        decision_record=decision_path,
        m029_authorization=authorization_path,
    )
    report_path = tmp_path / "m028-report.json"
    write_lambda_m028_report(report_path, report)

    return {
        **paths,
        "valid_discovery": valid_discovery_path,
        "launch_plan": Path(m020.launch_plan_ref),
        "lambda_teardown": Path(m020.teardown_plan_ref),
        "snapshot": snapshot_path,
        "budget": budget_path,
        "resource": resource_path,
        "window": window_path,
        "final_teardown": teardown_path,
        "operator": operator_path,
        "no_mutation": no_mutation_path,
        "m029_authorization": authorization_path,
        "m028_decision": decision_path,
        "m028_report": report_path,
    }
