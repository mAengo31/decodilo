from __future__ import annotations

import json
import shutil
from pathlib import Path

from decodilo.lambda_cloud.l1_runtime_evidence_package import (
    build_lambda_l1_runtime_evidence_package_from_dir,
    load_lambda_l1_runtime_evidence_package,
    write_lambda_l1_runtime_evidence_package,
)


def test_lambda_l1_runtime_evidence_package_validates_persisted_artifacts() -> None:
    evidence_dir = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "evidence"
        / "lambda_l1_adamw_nesterov_1bada235b"
    )

    package = build_lambda_l1_runtime_evidence_package_from_dir(evidence_dir)

    assert package.evidence_complete is True
    assert package.lambda_l1_runtime_passed is True
    assert package.production_scale_ready is False
    assert package.multi_instance_distributed_ready is False
    assert package.pathway_operation_layer_ready is False
    assert package.final_instance_count == 0
    assert package.billable_action_performed is True
    assert package.billable_action_scope == "historical_single_lambda_instance_verification"
    assert package.launch_ready is False
    assert package.launch_allowed is False
    assert package.inner_optimizer_semantics == "adamw"
    assert package.outer_optimizer_semantics == "nesterov"
    assert package.committed_sync_rounds == 9
    assert package.final_global_version == 9
    assert package.accepted_updates == 18
    assert package.useful_tokens_accepted == 1890
    assert package.pseudo_gradient_numeric_check_passed is True
    assert package.pseudo_gradient_numeric_rounds_checked == 9
    assert package.independent_nesterov_max_abs_error == 0.0
    assert package.checkpoint_outer_optimizer_step == 9
    assert package.checkpoint_velocity_max_abs_error == 0.0
    assert package.replay_passed is True
    assert package.metric_validation_passed is True
    assert set(package.learner_artifacts_present) == {"learner-0", "learner-1"}
    assert package.missing_items == []
    assert package.blockers == []
    assert package.secret_scan_passed is True


def test_lambda_l1_runtime_evidence_package_detects_tampered_events(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "evidence"
        / "lambda_l1_adamw_nesterov_1bada235b"
    )
    workdir = tmp_path / "tampered"
    shutil.copytree(source, workdir)

    events_path = workdir / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        event = json.loads(line)
        if event["event_type"] == "sync_round_committed":
            event["payload"]["new_global_vector"][0] += 0.001
            lines[index] = json.dumps(event, separators=(",", ":"))
            break
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    package = build_lambda_l1_runtime_evidence_package_from_dir(workdir)

    assert package.evidence_complete is False
    assert package.lambda_l1_runtime_passed is False
    assert package.pseudo_gradient_numeric_check_passed is False
    assert package.independent_nesterov_max_abs_error >= 0.001
    assert "pseudo_gradient_numeric_check_failed" in package.blockers


def test_lambda_l1_runtime_evidence_package_roundtrips(tmp_path: Path) -> None:
    evidence_dir = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "evidence"
        / "lambda_l1_adamw_nesterov_1bada235b"
    )
    package = build_lambda_l1_runtime_evidence_package_from_dir(evidence_dir)
    output = tmp_path / "lambda_l1_evidence_package.json"

    write_lambda_l1_runtime_evidence_package(output, package)
    loaded = load_lambda_l1_runtime_evidence_package(output)

    assert loaded == package
