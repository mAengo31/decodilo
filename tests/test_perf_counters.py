from decodilo.runtime.perf_counters import PerfTimer, nonnegative_perf_counters


def test_perf_counters_are_nonnegative() -> None:
    timer = PerfTimer()
    counters = nonnegative_perf_counters(wall_time_seconds=timer.elapsed())

    assert counters.wall_time_seconds >= 0
    assert counters.bytes_serialized >= 0
    assert counters.transport_messages_sent >= 0

