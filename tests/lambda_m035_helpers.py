from __future__ import annotations

from pathlib import Path

from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m034d_helpers import closed_m034_incident

from decodilo.lambda_cloud.fourth_attempt_option_matrix import (
    build_lambda_fourth_attempt_option_matrix,
)
from decodilo.lambda_cloud.launch_attempt_history import (
    build_lambda_launch_attempt_history_report,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    build_lambda_launch_endpoint_confidence_review,
)
from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs
from decodilo.lambda_cloud.launch_shape_strategy_review import (
    build_lambda_launch_shape_strategy_review,
)
from decodilo.lambda_cloud.m035_decision_record import build_lambda_m035_decision_record
from decodilo.lambda_cloud.support_evidence_request import (
    build_lambda_support_evidence_request,
)
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
)


def attempt_history(tmp_path: Path):
    return build_lambda_launch_attempt_history_report(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m034_incident=closed_m034_incident(tmp_path),
    )


def endpoint_verification(confidence: str = "medium"):
    return verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="POST",
                path_template="/instance-operations/launch",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence=confidence,
            ),
            build_lambda_endpoint_spec(
                operation="terminate_owned_instance",
                method="POST",
                path_template="/instance-operations/terminate",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence=confidence,
            ),
        ]
    )


def endpoint_confidence(tmp_path: Path, confidence: str = "medium"):
    return build_lambda_launch_endpoint_confidence_review(
        endpoint_verification=endpoint_verification(confidence),
        attempt_history=attempt_history(tmp_path),
    )


def price_snapshot(sample: bool = False) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id="lambda-test-catalog",
        provider="lambda",
        captured_at_utc="2026-06-19T00:00:00Z",
        source_url="https://lambda.ai/instances",
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="a" * 64,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                product_family="on_demand_instance",
                instance_type="gpu_8x_h100_sxm",
                gpu_type="H100 SXM",
                gpus_per_instance=8,
                price_per_gpu_hour=3.99,
                price_per_instance_hour=31.92,
                captured_at_utc="2026-06-19T00:00:00Z",
                record_id="lambda:gpu_8x_h100_sxm:0",
            ),
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
        ],
        notes="test catalog",
        is_sample_data=sample,
    )


def shape_strategy():
    return build_lambda_launch_shape_strategy_review(
        price_snapshot=price_snapshot(),
        current_shape="gpu_8x_h100_sxm",
    )


def option_matrix(tmp_path: Path, confidence: str = "medium"):
    return build_lambda_fourth_attempt_option_matrix(
        attempt_history=attempt_history(tmp_path),
        endpoint_confidence=endpoint_confidence(tmp_path, confidence),
        shape_strategy=shape_strategy(),
    )


def decision(tmp_path: Path, confidence: str = "medium"):
    return build_lambda_m035_decision_record(option_matrix(tmp_path, confidence))


def support_request():
    return build_lambda_support_evidence_request()
