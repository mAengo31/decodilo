import ast
from pathlib import Path


def test_m033_does_not_introduce_enabled_launch_flags():
    root = Path("src/decodilo/lambda_cloud")
    m033_files = [
        root / "endpoint_spec_operator_confirmation.py",
        root / "response_capture_settings_lock.py",
        root / "launch_timeout_policy.py",
        root / "third_attempt_review.py",
        root / "third_attempt_risk_review.py",
        root / "third_attempt_authorization.py",
        root / "third_attempt_go_no_go.py",
        root / "third_attempt_correlation_plan.py",
        root / "third_attempt_reconciliation_plan.py",
        root / "m034_authorization_record.py",
        root / "m033_report.py",
    ]
    offenders: list[tuple[str, str]] = []
    for path in m033_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg in {
                "launch_ready",
                "launch_allowed",
                "real_mutation_enabled",
                "billable_action_performed",
            }:
                if isinstance(node.value, ast.Constant) and node.value.value is True:
                    offenders.append((str(path), node.arg))
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id
                        in {
                            "launch_ready",
                            "launch_allowed",
                            "real_mutation_enabled",
                            "billable_action_performed",
                        }
                        and isinstance(node.value, ast.Constant)
                        and node.value.value is True
                    ):
                        offenders.append((str(path), target.id))

    assert offenders == []
