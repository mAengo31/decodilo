from decodilo.runtime.update_stream import UpdateStream


def test_update_metric_semantics_count_messages_acks_and_duplicates() -> None:
    stream = UpdateStream()
    stream.register("learner-0", version=0)
    stream.notify_commit(global_version=1)
    stream.mark_sent("learner-0", global_version=1)
    stream.ack("learner-0", global_version=1, current_version=1)
    stream.ack("learner-0", global_version=1, current_version=1)

    metrics = stream.metrics_dict()
    assert metrics["global_update_broadcasts"] == 1
    assert metrics["global_update_messages_sent"] == 1
    assert metrics["global_update_acks"] == 1
    assert metrics["duplicate_global_update_acks"] == 1
    assert metrics["missing_global_update_acks"] == 0
    assert metrics["learner_update_lag_current"] == {"learner-0": 0}
