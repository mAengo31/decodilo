from decodilo.runtime.metrics_validation import validate_metrics


def test_metric_validation_passes_and_fails_expected_invariants() -> None:
    good = {
        "total_tokens_processed": 100,
        "useful_tokens_accepted": 80,
        "wasted_tokens": 20,
        "goodput_ratio": 0.8,
        "global_update_messages_sent": 2,
        "global_update_acks": 2,
        "duplicate_global_update_acks": 1,
        "committed_sync_rounds": 2,
    }
    assert validate_metrics(good, final_global_version=2).passed is True

    bad = dict(good)
    bad["wasted_tokens"] = 999
    bad["global_update_acks"] = 3
    result = validate_metrics(bad, final_global_version=2)
    assert result.passed is False
    assert len(result.errors) == 2
