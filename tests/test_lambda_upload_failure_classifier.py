from __future__ import annotations

from lambda_m073s_helpers import make_m073r_upload_failure_workdir

from decodilo.lambda_cloud.upload_failure_classifier import (
    build_lambda_upload_failure_classification_from_workdir,
    classify_upload_failure_text,
)


def test_upload_failure_classifier_detects_banner_timeout_text() -> None:
    assert (
        classify_upload_failure_text(
            "Connection timed out during banner exchange\nscp: Connection closed"
        )
        == "ssh_banner_exchange_timeout_during_upload"
    )


def test_upload_failure_classifier_detects_scp_connection_closed() -> None:
    assert (
        classify_upload_failure_text("kex_exchange_identification: banner exchange timeout")
        == "ssh_banner_exchange_timeout_during_upload"
    )
    assert (
        classify_upload_failure_text("Connection closed by remote host")
        == "scp_connection_closed_during_upload"
    )


def test_upload_failure_classifier_marks_decodilo_not_tested(tmp_path):
    workdir, _post = make_m073r_upload_failure_workdir(tmp_path)

    report = build_lambda_upload_failure_classification_from_workdir(workdir=workdir)

    assert report.failure_stage == "source_bundle_upload"
    assert report.failure_classification == "ssh_banner_exchange_timeout_during_upload"
    assert report.source_bundle_upload_attempted is True
    assert report.source_bundle_upload_verified is False
    assert report.dependency_bundle_upload_attempted is False
    assert report.manifest_started is False
    assert report.tiny_smoke_attempted is False
    assert report.decodilo_tested is False
    assert report.termination_verified is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False
