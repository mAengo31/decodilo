from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.fake_launch_executor import execute_fake_lambda_launch
from decodilo.lambda_cloud.fake_launch_readiness_package import (
    build_fake_lambda_launch_readiness_package,
)
from decodilo.lambda_cloud.fake_lifecycle_preflight import (
    run_fake_lambda_lifecycle_preflight,
    write_fake_lambda_lifecycle_preflight_report,
)
from decodilo.lambda_cloud.fake_lifecycle_stress import (
    run_fake_lambda_lifecycle_stress,
    write_fake_lambda_lifecycle_stress_report,
)
from decodilo.lambda_cloud.fake_teardown_audit import (
    audit_fake_lambda_teardown,
    write_fake_lambda_teardown_audit_report,
)
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown


def _package_inputs(tmp_path):
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=approval_path,
    )
    preflight_path = tmp_path / "preflight.json"
    write_fake_lambda_lifecycle_preflight_report(preflight_path, preflight)
    stress = run_fake_lambda_lifecycle_stress(
        m020_report=m020_path,
        approval_manifest=approval_path,
        workdir=tmp_path / "stress",
        cycles=1,
        failure_modes=["none"],
    )
    stress_path = tmp_path / "stress.json"
    write_fake_lambda_lifecycle_stress_report(stress_path, stress)
    launch = execute_fake_lambda_launch(
        m020_report_path=m020_path,
        approval_manifest_path=approval_path,
        workdir=tmp_path / "life",
        idempotency_key="fake-launch-001",
    )
    launch_path = tmp_path / "life" / "launch.json"
    launch_path.write_text(launch.to_json(), encoding="utf-8")
    teardown = execute_fake_lambda_teardown(lifecycle_report_path=launch_path)
    teardown_path = tmp_path / "life" / "teardown.json"
    teardown_path.write_text(teardown.to_json(), encoding="utf-8")
    audit = audit_fake_lambda_teardown(
        lifecycle_report=launch_path,
        teardown_report=teardown_path,
    )
    audit_path = tmp_path / "teardown-audit.json"
    write_fake_lambda_teardown_audit_report(audit_path, audit)
    return m020_path, approval_path, preflight_path, stress_path, audit_path


def test_fake_launch_readiness_package_builds_from_complete_evidence(tmp_path) -> None:
    inputs = _package_inputs(tmp_path)

    package = build_fake_lambda_launch_readiness_package(
        m020_report=inputs[0],
        approval_manifest=inputs[1],
        preflight_report=inputs[2],
        stress_report=inputs[3],
        teardown_audit=inputs[4],
        project_root=".",
    )

    assert package.blockers == []
    assert package.future_real_launch_candidate is False
    assert package.launch_allowed is False
    assert package.evidence_hashes


def test_fake_launch_readiness_package_blocks_missing_teardown_audit(tmp_path) -> None:
    inputs = _package_inputs(tmp_path)

    package = build_fake_lambda_launch_readiness_package(
        m020_report=inputs[0],
        approval_manifest=inputs[1],
        preflight_report=inputs[2],
        stress_report=inputs[3],
        teardown_audit=tmp_path / "missing.json",
        project_root=".",
    )

    assert any("missing evidence: teardown_audit" in blocker for blocker in package.blockers)
