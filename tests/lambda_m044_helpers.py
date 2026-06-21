from __future__ import annotations

from pathlib import Path

from lambda_m040_helpers import write_m040_inputs

from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    build_lambda_capacity_aware_retry_policy_from_path,
    write_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_history import (
    build_lambda_capacity_history_from_paths,
    write_lambda_capacity_history,
)
from decodilo.lambda_cloud.catalog_candidate_rotation import (
    build_lambda_catalog_candidate_rotation_from_paths,
    write_lambda_catalog_candidate_rotation,
)
from decodilo.lambda_cloud.catalog_rotation_command_preview import (
    build_lambda_catalog_rotation_command_preview_from_path,
    write_lambda_catalog_rotation_command_preview,
)
from decodilo.lambda_cloud.catalog_rotation_cost_review import (
    build_lambda_catalog_rotation_cost_review_from_paths,
    write_lambda_catalog_rotation_cost_review,
)
from decodilo.lambda_cloud.catalog_rotation_operator_decision import (
    build_lambda_catalog_rotation_operator_decision_from_path,
    write_lambda_catalog_rotation_operator_decision,
)
from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    build_lambda_catalog_rotation_risk_acceptance,
    write_lambda_catalog_rotation_risk_acceptance,
)
from decodilo.lambda_cloud.catalog_rotation_shape_authorization import (
    build_lambda_catalog_rotation_shape_authorization_from_paths,
    write_lambda_catalog_rotation_shape_authorization,
)
from decodilo.lambda_cloud.catalog_rotation_wait_plan import (
    build_lambda_catalog_rotation_wait_plan_from_path,
    write_lambda_catalog_rotation_wait_plan,
)
from decodilo.lambda_cloud.m044_decision_record import (
    build_lambda_m044_decision_record_from_paths,
    write_lambda_m044_decision_record,
)
from decodilo.lambda_cloud.m044_report import (
    build_lambda_m044_report_from_paths,
    write_lambda_m044_report,
)
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    write_price_snapshot,
)


def m044_price_snapshot(*, sample: bool = False, over_budget: bool = False) -> PriceSnapshot:
    a100_hourly = 200.0 if over_budget else 22.32
    return PriceSnapshot(
        snapshot_id="lambda-test-catalog-m044",
        provider="lambda",
        captured_at_utc="2026-06-19T00:00:00Z",
        source_url="https://lambda.ai/instances",
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="b" * 64,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                product_family="on_demand_instance",
                instance_type="gpu_1x_h100_pcie",
                gpu_type="H100 PCIe",
                gpus_per_instance=1,
                price_per_gpu_hour=3.29,
                price_per_instance_hour=3.29,
                captured_at_utc="2026-06-19T00:00:00Z",
                record_id="lambda:gpu_1x_h100_pcie:1",
            ),
            SnapshotPriceRecord(
                provider="lambda",
                product_family="on_demand_instance",
                instance_type="gpu_8x_a100_80gb_sxm4",
                gpu_type="A100 SXM 80GB",
                gpus_per_instance=8,
                price_per_gpu_hour=2.79 if not over_budget else 25.0,
                price_per_instance_hour=a100_hourly,
                captured_at_utc="2026-06-19T00:00:00Z",
                record_id="lambda:gpu_8x_a100_80gb_sxm4:2",
            ),
        ],
        notes="M044 test catalog",
        is_sample_data=sample,
    )


def write_m044_inputs(
    tmp_path: Path,
    *,
    accept: bool = True,
    decline_wait: bool = False,
    decline_manual: bool = False,
    sample_price: bool = False,
    over_budget: bool = False,
) -> dict[str, Path]:
    paths = write_m040_inputs(tmp_path)
    paths.update(
        {
            "history": tmp_path / "capacity-history.json",
            "retry": tmp_path / "retry-policy.json",
            "rotation": tmp_path / "catalog-rotation.json",
            "cost": tmp_path / "catalog-rotation-cost-review.json",
            "risk": tmp_path / "catalog-rotation-risk-acceptance.json",
            "operator": tmp_path / "catalog-rotation-operator-decision.json",
            "wait": tmp_path / "catalog-rotation-wait-plan.json",
            "authorization_m045": tmp_path / "m045-authorization.json",
            "preview_m045": tmp_path / "m045-command-preview.json",
            "decision_m044": tmp_path / "m044-decision.json",
            "m044": tmp_path / "m044-report.json",
        }
    )
    write_price_snapshot(
        paths["prices"],
        m044_price_snapshot(sample=sample_price, over_budget=over_budget),
    )
    history = build_lambda_capacity_history_from_paths(
        latest_closeout=paths["closeout"],
        previous_closeout=paths["closeout"],
    )
    write_lambda_capacity_history(paths["history"], history)
    retry = build_lambda_capacity_aware_retry_policy_from_path(history=paths["history"])
    write_lambda_capacity_aware_retry_policy(paths["retry"], retry)
    rotation = build_lambda_catalog_candidate_rotation_from_paths(
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        ssh_key_selection=paths["ssh"],
    )
    write_lambda_catalog_candidate_rotation(paths["rotation"], rotation)
    cost = build_lambda_catalog_rotation_cost_review_from_paths(
        rotation_rank=paths["rotation"],
        price_snapshot=paths["prices"],
    )
    write_lambda_catalog_rotation_cost_review(paths["cost"], cost)
    risk = build_lambda_catalog_rotation_risk_acceptance(
        accept_selected_candidate=accept,
        decline_wait=decline_wait,
        decline_manual_selection=decline_manual,
        acknowledge_all=accept,
    )
    write_lambda_catalog_rotation_risk_acceptance(paths["risk"], risk)
    operator = build_lambda_catalog_rotation_operator_decision_from_path(paths["risk"])
    write_lambda_catalog_rotation_operator_decision(paths["operator"], operator)
    wait = build_lambda_catalog_rotation_wait_plan_from_path(paths["operator"])
    write_lambda_catalog_rotation_wait_plan(paths["wait"], wait)
    auth = build_lambda_catalog_rotation_shape_authorization_from_paths(
        capacity_history=paths["history"],
        retry_policy=paths["retry"],
        rotation_rank=paths["rotation"],
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_catalog_rotation_shape_authorization(paths["authorization_m045"], auth)
    preview = build_lambda_catalog_rotation_command_preview_from_path(
        paths["authorization_m045"]
    )
    write_lambda_catalog_rotation_command_preview(paths["preview_m045"], preview)
    decision = build_lambda_m044_decision_record_from_paths(
        operator_decision=paths["operator"],
        authorization=paths["authorization_m045"],
    )
    write_lambda_m044_decision_record(paths["decision_m044"], decision)
    report = build_lambda_m044_report_from_paths(
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        decision=paths["decision_m044"],
        authorization=paths["authorization_m045"],
        command_preview=paths["preview_m045"],
        wait_plan=paths["wait"],
    )
    write_lambda_m044_report(paths["m044"], report)
    return paths
