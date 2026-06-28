from __future__ import annotations

from lambda_m073s_helpers import make_m073r_upload_failure_workdir

from decodilo.lambda_cloud.remote_vslice_upload_closeout import (
    build_lambda_remote_vslice_upload_closeout_from_paths,
)
from decodilo.lambda_cloud.upload_failure_classifier import (
    build_lambda_upload_failure_classification_from_workdir,
    write_lambda_upload_failure_classification,
)


def test_upload_closeout_closes_banner_timeout_without_decodilo_blame(tmp_path):
    workdir, post = make_m073r_upload_failure_workdir(tmp_path)
    classification_path = tmp_path / "classification.json"
    write_lambda_upload_failure_classification(
        classification_path,
        build_lambda_upload_failure_classification_from_workdir(workdir=workdir),
    )

    closeout = build_lambda_remote_vslice_upload_closeout_from_paths(
        classification=classification_path,
        post_discovery=post,
    )

    assert closeout.closeout_status == "closed_source_upload_ssh_banner_timeout"
    assert closeout.closeout_succeeded is True
    assert closeout.source_bundle_uploaded is False
    assert closeout.dependency_bundle_uploaded is False
    assert closeout.tiny_smoke_attempted is False
    assert closeout.decodilo_not_tested is True
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
