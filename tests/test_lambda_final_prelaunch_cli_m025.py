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


def test_final_prelaunch_cli_success_path(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    evidence_out = tmp_path / "cli-evidence.json"
    semantic_out = tmp_path / "cli-semantic.json"
    checklist_out = tmp_path / "cli-checklist.json"
    review_out = tmp_path / "cli-review.json"
    go_out = tmp_path / "cli-go.json"

    evidence = _run(
        "lambda",
        "final-prelaunch",
        "evidence-package",
        "--m019c-discovery",
        str(paths["discovery"]),
        "--m019c-audit",
        str(paths["audit"]),
        "--m020-report",
        str(paths["m020"]),
        "--m022-readiness-package",
        str(paths["readiness"]),
        "--m023-evidence-package",
        str(paths["m023_package"]),
        "--m024-skeleton-audit",
        str(paths["skeleton"]),
        "--out",
        str(evidence_out),
    )
    semantic = _run(
        "lambda",
        "final-prelaunch",
        "semantic-audit",
        "--project-root",
        ".",
        "--out",
        str(semantic_out),
    )
    checklist = _run(
        "lambda",
        "final-prelaunch",
        "checklist-template",
        "--acknowledge-all",
        "--out",
        str(checklist_out),
    )
    review = _run(
        "lambda",
        "final-prelaunch",
        "review",
        "--evidence-package",
        str(evidence_out),
        "--operator-checklist",
        str(checklist_out),
        "--semantic-audit",
        str(semantic_out),
        "--out",
        str(review_out),
    )
    go = _run(
        "lambda",
        "final-prelaunch",
        "go-no-go",
        "--review",
        str(review_out),
        "--out",
        str(go_out),
    )

    assert evidence["evidence_complete"] is True
    assert semantic["passed"] is True
    assert checklist["review_only_complete"] is True
    assert review["go_no_go_recommendation"] == "go_for_future_m026_real_launch_review"
    assert go["status"] == "go_for_future_m026_real_launch_review"
    assert go["launch_allowed"] is False
