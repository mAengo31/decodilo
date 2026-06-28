from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.gpu_visibility_command_policy import M063_GPU_VISIBILITY_COMMAND
from decodilo.lambda_cloud.gpu_visibility_command_review import (
    build_lambda_gpu_visibility_command_review_from_paths,
)


def test_gpu_visibility_command_review_selects_exact_future_command(tmp_path):
    paths = write_m062_chain(tmp_path)

    review = build_lambda_gpu_visibility_command_review_from_paths(
        command_policy=paths["command_policy"],
        output_policy=paths["output_policy"],
    )

    assert review.command_review_status == "gpu_visibility_command_review_passed_future_only"
    assert review.selected_future_command_set == [M063_GPU_VISIBILITY_COMMAND]
    assert review.command_authorized_now is False
    assert review.no_package_install is True
    assert review.no_training is True
    assert review.launch_ready is False
