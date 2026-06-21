from __future__ import annotations

from pathlib import Path

from lambda_m035_helpers import price_snapshot
from lambda_m037r_helpers import controls, discovery, ssh_selection

from decodilo.lambda_cloud.availability_first_authorization_package import (
    build_lambda_availability_first_authorization_package,
    write_lambda_availability_first_authorization_package,
)
from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    rank_lambda_availability_first_candidates,
    write_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.availability_first_go_no_go import (
    build_lambda_availability_first_go_no_go,
    write_lambda_availability_first_go_no_go,
)
from decodilo.lambda_cloud.availability_first_launch_plan import (
    build_lambda_availability_first_launch_plan,
    write_lambda_availability_first_launch_plan,
)
from decodilo.lambda_cloud.capacity_error_closeout import (
    build_lambda_capacity_error_closeout,
    write_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.capacity_error_policy import (
    build_lambda_capacity_error_policy,
    write_lambda_capacity_error_policy,
)
from decodilo.lambda_cloud.launch_transport_error_taxonomy import (
    classify_lambda_launch_transport_error,
)
from decodilo.lambda_cloud.live_capacity_candidate_extractor import (
    extract_lambda_capacity_candidates,
    write_lambda_live_capacity_candidate_extractor,
)
from decodilo.lambda_cloud.live_discovery_report import write_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import LambdaM029Report
from decodilo.lambda_cloud.m040_report import build_lambda_m040_report_from_paths
from decodilo.lambda_cloud.real_launch_spend_audit import (
    LambdaM029SpendAuditReport,
    write_lambda_m029_spend_audit,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    LambdaTransportErrorPersistenceRecord,
)
from decodilo.pricing.snapshots import write_price_snapshot


def m039_capacity_report() -> LambdaM029Report:
    return LambdaM029Report(
        run_id="lambda-m039-lower-cost-launch",
        real_lambda_api_used=True,
        launch_request_sent=True,
        launch_response_received=True,
        owned_instance_id_redacted=None,
        termination_request_sent=False,
        termination_response_received=False,
        termination_verified=False,
        manual_review_required=True,
        mutating_operations=1,
        billable_action_performed=True,
        estimated_spend=0.001,
        elapsed_seconds=1.7,
        launch_timeout_seconds_effective=30.0,
        no_auto_launch_retry=True,
        response_capture_active=True,
        status_before_parse=True,
        launch_response_http_status=400,
        launch_response_content_type="application/json",
        launch_response_body_size_bytes=212,
        launch_response_classification="http_error_json",
        launch_response_error_message_redacted=(
            "Not enough capacity to fulfill launch request."
        ),
        lower_cost_path_used=True,
        selected_shape="gpu_1x_h100_pcie",
        selected_region="us-west-1",
        selected_ssh_key_hash="sha256:test",
        strand_payload_compatible=True,
        warnings=["termination not verified; manual review required"],
    )


def transport_error() -> LambdaTransportErrorPersistenceRecord:
    return LambdaTransportErrorPersistenceRecord(
        request_attempt_id="lambda-transport-error-test",
        operation="launch_one_instance",
        request_sent=True,
        status_code=400,
        reason="Bad Request",
        content_type="application/json",
        content_length=212,
        body_size_bytes=212,
        response_classification="http_error_json",
        exception_type="LambdaRealMutationTransportError",
        exception_message_redacted="M029 real Lambda HTTP error",
        provider_error_message_redacted="Not enough capacity to fulfill launch request.",
        elapsed_seconds=1.7,
        taxonomy=classify_lambda_launch_transport_error(
            status_code=400,
            response_classification="http_error_json",
            exception_type="LambdaRealMutationTransportError",
        ),
    )


def spend_audit() -> LambdaM029SpendAuditReport:
    return LambdaM029SpendAuditReport(
        estimated_hourly_cost=3.29,
        actual_elapsed_seconds=1.7,
        estimated_spend=0.001,
        budget_exceeded=False,
        runtime_exceeded=False,
        billable_action_performed=True,
        launch_request_sent=True,
        terminate_request_sent=False,
        termination_verified=False,
    )


def capacity_closeout():
    return build_lambda_capacity_error_closeout(
        m039_report=m039_capacity_report(),
        transport_error=transport_error(),
        post_discovery=discovery(),
        spend_audit=spend_audit(),
    )


def candidates(*, live: bool = False, sample_price: bool = False):
    return extract_lambda_capacity_candidates(
        discovery=discovery(include_shape=live),
        price_snapshot=price_snapshot(sample=sample_price),
    )


def rank(*, live: bool = False):
    return rank_lambda_availability_first_candidates(
        candidates=candidates(live=live),
        ssh_key_selection=ssh_selection(),
    )


def plan(*, live: bool = False):
    return build_lambda_availability_first_launch_plan(
        rank=rank(live=live),
        ssh_key_selection=ssh_selection(),
    )


def authorization(tmp_path: Path, *, live: bool = False):
    paths = write_m040_inputs(tmp_path, live=live)
    return build_lambda_availability_first_authorization_package(
        capacity_closeout=paths["closeout"],
        capacity_policy=paths["policy"],
        rank=paths["rank"],
        plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )


def write_m040_inputs(tmp_path: Path, *, live: bool = False) -> dict[str, Path]:
    paths = {
        "m039_report": tmp_path / "m039" / "report.json",
        "transport": tmp_path / "m039" / "transport-error.json",
        "spend": tmp_path / "m039" / "spend-audit.json",
        "discovery": tmp_path / "discovery.json",
        "prices": tmp_path / "prices.json",
        "ssh": tmp_path / "ssh.json",
        "controls": tmp_path / "controls.json",
        "closeout": tmp_path / "closeout.json",
        "policy": tmp_path / "policy.json",
        "candidates": tmp_path / "candidates.json",
        "rank": tmp_path / "rank.json",
        "plan": tmp_path / "plan.json",
        "authorization": tmp_path / "authorization.json",
        "go": tmp_path / "go.json",
        "report": tmp_path / "m040.json",
    }
    paths["m039_report"].parent.mkdir(parents=True)
    paths["m039_report"].write_text(m039_capacity_report().to_json(), encoding="utf-8")
    paths["transport"].write_text(transport_error().to_json(), encoding="utf-8")
    write_lambda_m029_spend_audit(paths["spend"], spend_audit())
    write_lambda_live_discovery_report(paths["discovery"], discovery(include_shape=live))
    write_price_snapshot(paths["prices"], price_snapshot())
    write_lambda_existing_ssh_key_selection(paths["ssh"], ssh_selection())
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    closeout_report = capacity_closeout()
    write_lambda_capacity_error_closeout(paths["closeout"], closeout_report)
    policy_report = build_lambda_capacity_error_policy(closeout=closeout_report)
    write_lambda_capacity_error_policy(paths["policy"], policy_report)
    candidates_report = candidates(live=live)
    write_lambda_live_capacity_candidate_extractor(paths["candidates"], candidates_report)
    rank_report = rank(live=live)
    write_lambda_availability_first_candidate_ranker(paths["rank"], rank_report)
    plan_report = plan(live=live)
    write_lambda_availability_first_launch_plan(paths["plan"], plan_report)
    auth = build_lambda_availability_first_authorization_package(
        capacity_closeout=paths["closeout"],
        capacity_policy=paths["policy"],
        rank=paths["rank"],
        plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_availability_first_authorization_package(paths["authorization"], auth)
    go = build_lambda_availability_first_go_no_go(auth)
    write_lambda_availability_first_go_no_go(paths["go"], go)
    report = build_lambda_m040_report_from_paths(
        capacity_closeout=paths["closeout"],
        availability_authorization=paths["authorization"],
        go_no_go=paths["go"],
    )
    paths["report"].write_text(report.to_json(), encoding="utf-8")
    return paths
