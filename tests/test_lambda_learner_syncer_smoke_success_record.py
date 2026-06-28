from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir

from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
    build_lambda_learner_syncer_smoke_success_record_from_paths,
)


def test_learner_syncer_smoke_success_record_classifies_m079r2_success(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)

    record = build_lambda_learner_syncer_smoke_success_record_from_paths(
        workdir=workdir,
    )

    assert record.success_status == "remote_learner_syncer_smoke_success"
    assert record.infrastructure_passed is True
    assert record.learner_syncer_smoke_command_passed is True
    assert record.learner_syncer_smoke_status == "passed"
    assert record.learner_syncer_exchange_check_passed is True
    assert record.update_or_commit_check_passed is True
    assert record.replay_or_metric_check_passed is True
    assert record.artifact_body_persisted is True
    assert record.parsed_summary_persisted is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
