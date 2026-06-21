import json
import subprocess
import sys

from lambda_m025_helpers import write_m025_core_artifacts


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_lambda_decision_cli_success_path(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    review_out = tmp_path / "human-review.json"
    validation_out = tmp_path / "human-review-validation.json"
    freshness_out = tmp_path / "freshness.json"
    matrix_out = tmp_path / "matrix.json"
    decision_out = tmp_path / "decision.json"
    authorization_out = tmp_path / "authorization.json"
    report_out = tmp_path / "report.json"

    template = _run(
        "lambda",
        "decision",
        "human-review-template",
        "--m025-evidence-package",
        str(paths["package"]),
        "--go-no-go",
        str(paths["go"]),
        "--requested-decision",
        "approve_m027_minimal_real_mutation_implementation",
        "--acknowledge-all",
        "--out",
        str(review_out),
    )
    validation = _run(
        "lambda",
        "decision",
        "validate-human-review",
        "--human-review",
        str(review_out),
        "--out",
        str(validation_out),
    )
    freshness = _run(
        "lambda",
        "decision",
        "freshness",
        "--m019c-discovery",
        str(paths["discovery"]),
        "--price-snapshot",
        str(paths["m020"]),
        "--m025-review",
        str(paths["review"]),
        "--semantic-audit",
        str(paths["semantic"]),
        "--out",
        str(freshness_out),
    )
    matrix = _run(
        "lambda",
        "decision",
        "blocker-matrix",
        "--human-review-validation",
        str(validation_out),
        "--freshness-report",
        str(freshness_out),
        "--semantic-audit",
        str(paths["semantic"]),
        "--out",
        str(matrix_out),
    )
    decision = _run(
        "lambda",
        "decision",
        "decide",
        "--human-review-validation",
        str(validation_out),
        "--freshness-report",
        str(freshness_out),
        "--blocker-matrix",
        str(matrix_out),
        "--m025-review",
        str(paths["review"]),
        "--out",
        str(decision_out),
    )
    authorization = _run(
        "lambda",
        "decision",
        "m027-authorization",
        "--decision-record",
        str(decision_out),
        "--out",
        str(authorization_out),
    )
    report = _run(
        "lambda",
        "decision",
        "report",
        "--decision-record",
        str(decision_out),
        "--authorization-record",
        str(authorization_out),
        "--human-review-validation",
        str(validation_out),
        "--freshness-report",
        str(freshness_out),
        "--blocker-matrix",
        str(matrix_out),
        "--out",
        str(report_out),
    )

    assert template["human_review_complete"] is True
    assert validation["human_review_valid_for_m027_authorization"] is True
    assert freshness["freshness_passed"] is True
    assert matrix["m027_authorization_blocked"] is False
    assert decision["status"] == "approve_m027_minimal_real_mutation_implementation"
    assert (
        authorization["status"]
        == "authorized_to_implement_minimal_mutation_code_disabled_by_default"
    )
    assert report["decision_status"] == "approve_m027_minimal_real_mutation_implementation"
    assert report["launch_allowed"] is False
