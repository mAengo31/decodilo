from __future__ import annotations

from lambda_m073s_helpers import (
    make_future_tiny_smoke_authorization,
    make_m073r_upload_failure_workdir,
)

from decodilo.lambda_cloud.m073r2_retry_authorization import (
    build_lambda_m073r2_retry_authorization_from_paths,
    write_lambda_m073r2_retry_authorization,
)
from decodilo.lambda_cloud.m073r2_runbook_preview import (
    build_lambda_m073r2_runbook_preview_from_paths,
    write_lambda_m073r2_runbook_preview,
)
from decodilo.lambda_cloud.m073s_report import build_lambda_m073s_report_from_paths
from decodilo.lambda_cloud.remote_vslice_upload_closeout import (
    build_lambda_remote_vslice_upload_closeout_from_paths,
    write_lambda_remote_vslice_upload_closeout,
)
from decodilo.lambda_cloud.source_bundle_upload_policy import (
    build_lambda_source_dependency_upload_policy_from_path,
    write_lambda_source_dependency_upload_policy,
)
from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    build_lambda_ssh_banner_readiness_policy,
    write_lambda_ssh_banner_readiness_policy,
)
from decodilo.lambda_cloud.upload_failure_classifier import (
    build_lambda_upload_failure_classification_from_workdir,
    write_lambda_upload_failure_classification,
)
from decodilo.lambda_cloud.upload_readiness_policy import (
    build_lambda_upload_readiness_gate_policy_from_path,
    write_lambda_upload_readiness_gate_policy,
)


def test_m073s_report_passes_for_upload_readiness_closeout(tmp_path):
    workdir, post = make_m073r_upload_failure_workdir(tmp_path)
    classification = tmp_path / "classification.json"
    closeout = tmp_path / "closeout.json"
    banner = tmp_path / "banner.json"
    gate = tmp_path / "gate.json"
    upload_policy = tmp_path / "upload-policy.json"
    tiny_auth = make_future_tiny_smoke_authorization(tmp_path / "tiny-auth.json")
    authorization = tmp_path / "authorization.json"
    runbook = tmp_path / "runbook.json"
    write_lambda_upload_failure_classification(
        classification,
        build_lambda_upload_failure_classification_from_workdir(workdir=workdir),
    )
    write_lambda_remote_vslice_upload_closeout(
        closeout,
        build_lambda_remote_vslice_upload_closeout_from_paths(
            classification=classification,
            post_discovery=post,
        ),
    )
    write_lambda_ssh_banner_readiness_policy(
        banner,
        build_lambda_ssh_banner_readiness_policy(),
    )
    write_lambda_upload_readiness_gate_policy(
        gate,
        build_lambda_upload_readiness_gate_policy_from_path(banner_policy=banner),
    )
    write_lambda_source_dependency_upload_policy(
        upload_policy,
        build_lambda_source_dependency_upload_policy_from_path(
            upload_readiness_gate=gate,
        ),
    )
    write_lambda_m073r2_retry_authorization(
        authorization,
        build_lambda_m073r2_retry_authorization_from_paths(
            upload_closeout=closeout,
            upload_policy=upload_policy,
            tiny_smoke_authorization=tiny_auth,
        ),
    )
    write_lambda_m073r2_runbook_preview(
        runbook,
        build_lambda_m073r2_runbook_preview_from_paths(
            authorization=authorization,
            upload_policy=upload_policy,
        ),
    )

    report = build_lambda_m073s_report_from_paths(
        classification=classification,
        closeout=closeout,
        banner_policy=banner,
        upload_policy=upload_policy,
        authorization=authorization,
        runbook_preview=runbook,
    )

    assert report.report_passed is True
    assert report.classification == "ssh_banner_exchange_timeout_during_upload"
    assert report.closeout_status == "closed_source_upload_ssh_banner_timeout"
    assert report.decodilo_not_tested is True
    assert report.m073r2_authorization_status == (
        "authorized_for_future_m073r2_tiny_smoke_retry"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
