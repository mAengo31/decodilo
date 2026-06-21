from decodilo.storage.remote_backend_bandwidth_accounting import (
    build_remote_backend_bandwidth_accounting,
)


def test_bandwidth_accounting_sums_categories() -> None:
    report = build_remote_backend_bandwidth_accounting(
        learner_count=4,
        per_learner_traffic_bytes=100,
        syncer_traffic_bytes=50,
        replay_traffic_bytes=25,
        checkpoint_traffic_bytes=25,
        retry_overhead_ratio=0.1,
    )

    assert report.per_learner_traffic_bytes == 400
    assert report.retry_overhead_bytes == 50
    assert report.total_bytes == 550
    assert report.put_bytes == 425


def test_per_learner_traffic_scales_with_learner_count() -> None:
    small = build_remote_backend_bandwidth_accounting(
        learner_count=1,
        per_learner_traffic_bytes=100,
        syncer_traffic_bytes=0,
        replay_traffic_bytes=0,
        checkpoint_traffic_bytes=0,
    )
    large = build_remote_backend_bandwidth_accounting(
        learner_count=8,
        per_learner_traffic_bytes=100,
        syncer_traffic_bytes=0,
        replay_traffic_bytes=0,
        checkpoint_traffic_bytes=0,
    )

    assert large.total_bytes == small.total_bytes * 8
