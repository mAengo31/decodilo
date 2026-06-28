from __future__ import annotations

from lambda_m064_helpers import GPU_COMMAND, write_m063_gpu_visibility_workdir

from decodilo.lambda_cloud.gpu_visibility_success_record import (
    build_lambda_gpu_visibility_success_record_from_paths,
)


def test_gpu_visibility_success_record_passes_with_parsed_fields(tmp_path):
    paths = write_m063_gpu_visibility_workdir(tmp_path, parsed_fields=True)

    record = build_lambda_gpu_visibility_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status == "gpu_visibility_query_success"
    assert record.command == GPU_COMMAND
    assert record.parsed_gpu_name == "NVIDIA A10"
    assert record.parsed_fields_present is True
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_gpu_visibility_success_record_allows_hash_only_warning(tmp_path):
    paths = write_m063_gpu_visibility_workdir(tmp_path)

    record = build_lambda_gpu_visibility_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status == "gpu_visibility_query_executed_output_hash_only"
    assert record.stdout_hash_prefix == "af542830259dac01"
    assert record.parsed_fields_present is False
    assert record.blockers == []


def test_gpu_visibility_success_record_blocks_wrong_command(tmp_path):
    paths = write_m063_gpu_visibility_workdir(tmp_path, remote_command="nvidia-smi")

    record = build_lambda_gpu_visibility_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status != "gpu_visibility_query_success"
    assert "remote_command_not_exact_gpu_visibility_query" in record.blockers


def test_gpu_visibility_success_record_blocks_training(tmp_path):
    paths = write_m063_gpu_visibility_workdir(tmp_path, training_attempted=True)

    record = build_lambda_gpu_visibility_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status != "gpu_visibility_query_success"
    assert "training_attempted" in record.blockers
