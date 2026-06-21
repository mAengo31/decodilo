from __future__ import annotations

from pathlib import Path

from lambda_m040_helpers import write_m040_inputs

from decodilo.lambda_cloud.alternative_shape_operator_selection import (
    build_lambda_alternative_shape_operator_selection_from_paths,
    write_lambda_alternative_shape_operator_selection,
)
from decodilo.lambda_cloud.capacity_aware_report_semantics import (
    build_lambda_capacity_aware_run_semantics_from_path,
    write_lambda_capacity_aware_run_semantics,
)
from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    build_lambda_capacity_aware_retry_policy_from_path,
    write_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_followup_report import (
    build_lambda_capacity_followup_from_paths,
    write_lambda_capacity_followup,
)
from decodilo.lambda_cloud.capacity_history import (
    build_lambda_capacity_history_from_paths,
    write_lambda_capacity_history,
)
from decodilo.lambda_cloud.catalog_candidate_rotation import (
    build_lambda_catalog_candidate_rotation_from_paths,
    write_lambda_catalog_candidate_rotation,
)
from decodilo.lambda_cloud.m043_decision_record import (
    build_lambda_m043_decision_record_from_paths,
    write_lambda_m043_decision_record,
)
from decodilo.lambda_cloud.m043_report import build_lambda_m043_report_from_path


def write_m043_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = write_m040_inputs(tmp_path)
    paths["latest_closeout"] = tmp_path / "latest-closeout.json"
    paths["latest_closeout"].write_text(
        paths["closeout"].read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    paths.update(
        {
            "history": tmp_path / "capacity-history.json",
            "followup": tmp_path / "capacity-followup.json",
            "semantics": tmp_path / "capacity-semantics.json",
            "rotation": tmp_path / "catalog-rotation.json",
            "retry": tmp_path / "retry-policy.json",
            "selection": tmp_path / "operator-selection.json",
            "decision": tmp_path / "m043-decision.json",
            "m043": tmp_path / "m043-report.json",
        }
    )
    history = build_lambda_capacity_history_from_paths(
        latest_closeout=paths["latest_closeout"],
        previous_closeout=paths["closeout"],
    )
    write_lambda_capacity_history(paths["history"], history)
    followup = build_lambda_capacity_followup_from_paths(
        history=paths["history"],
        latest_closeout=paths["latest_closeout"],
        latest_discovery=paths["discovery"],
    )
    write_lambda_capacity_followup(paths["followup"], followup)
    semantics = build_lambda_capacity_aware_run_semantics_from_path(
        paths["latest_closeout"]
    )
    write_lambda_capacity_aware_run_semantics(paths["semantics"], semantics)
    rotation = build_lambda_catalog_candidate_rotation_from_paths(
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        ssh_key_selection=paths["ssh"],
    )
    write_lambda_catalog_candidate_rotation(paths["rotation"], rotation)
    retry = build_lambda_capacity_aware_retry_policy_from_path(history=paths["history"])
    write_lambda_capacity_aware_retry_policy(paths["retry"], retry)
    selection = build_lambda_alternative_shape_operator_selection_from_paths(
        rotation_rank=paths["rotation"],
        choose_catalog_candidate=True,
    )
    write_lambda_alternative_shape_operator_selection(paths["selection"], selection)
    decision = build_lambda_m043_decision_record_from_paths(
        capacity_followup=paths["followup"],
        rotation_rank=paths["rotation"],
        retry_policy=paths["retry"],
        operator_selection=paths["selection"],
    )
    write_lambda_m043_decision_record(paths["decision"], decision)
    report = build_lambda_m043_report_from_path(paths["decision"])
    paths["m043"].write_text(report.to_json(), encoding="utf-8")
    return paths
