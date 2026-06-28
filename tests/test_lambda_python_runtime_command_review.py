from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.python_runtime_command_review import (
    build_lambda_python_runtime_command_review_from_paths,
)


def test_python_runtime_command_review_passes_future_only(tmp_path):
    paths = write_m064_chain(tmp_path)

    review = build_lambda_python_runtime_command_review_from_paths(
        command_policy=paths["python_command_policy"],
        output_policy=paths["python_output_policy"],
    )

    assert review.command_review_status == "python_runtime_command_review_passed_future_only"
    assert review.selected_command == "python3 --version"
    assert review.command_authorized_now is False
    assert review.launch_ready is False
    assert review.launch_allowed is False
