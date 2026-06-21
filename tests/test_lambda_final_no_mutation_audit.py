from lambda_m028_helpers import clean_no_mutation_audit

from decodilo.lambda_cloud.final_no_mutation_audit import (
    LambdaFinalNoMutationAudit,
    run_lambda_final_no_mutation_audit,
)


def test_clean_no_mutation_audit_model_passes():
    audit = clean_no_mutation_audit()

    assert audit.audit_passed is True
    assert audit.launch_allowed is False


def test_current_project_no_mutation_audit_passes():
    audit = run_lambda_final_no_mutation_audit(project_root=".")

    assert audit.audit_passed is True
    assert audit.no_real_mutation_path_detected is True
    assert audit.live_client_read_only is True


def test_synthetic_launch_flag_fails_model():
    audit = LambdaFinalNoMutationAudit(
        no_real_mutation_path_detected=False,
        no_real_post_put_patch_delete_detected=True,
        live_client_read_only=True,
        fake_only_paths_labeled=True,
        launch_flags_false=False,
        billable_action_false=True,
        audit_passed=False,
        blockers=["synthetic enabled flag"],
    )

    assert audit.audit_passed is False
    assert audit.blockers
