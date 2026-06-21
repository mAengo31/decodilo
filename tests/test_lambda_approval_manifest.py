import json

import pytest

from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    build_lambda_approval_template,
)


def test_lambda_approval_template_is_incomplete_and_non_launching() -> None:
    manifest = build_lambda_approval_template(
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
    )

    assert manifest.approval_status == "incomplete"
    assert manifest.launch_allowed is False
    assert json.loads(manifest.to_json())["approved_max_budget"] == 50.0


def test_lambda_approval_manifest_rejects_real_launch_review_status() -> None:
    with pytest.raises(ValueError, match="approved_for_future_real_launch_review"):
        LambdaHumanApprovalManifest(
            approval_id="bad",
            approved_instance_type="gpu_8x_h100_sxm",
            approved_region="us-west-1",
            approved_gpu_type="H100 SXM",
            approved_gpus_per_instance=8,
            approval_status="approved_for_future_real_launch_review",
        )
