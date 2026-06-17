from decodilo.syncer.out_of_core_merge import (
    logical_metadata_merge_plan,
    metadata_only_out_of_core_merge,
)
from decodilo.trainer.synthetic_large_state import SyntheticLargeStateSource


def test_synthetic_large_state_metadata_only_merge_avoids_huge_allocation(tmp_path) -> None:
    source = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        logical_parameter_count=500_000_000,
        bytes_per_parameter=2,
    )
    manifest = source.manifest()
    plan = logical_metadata_merge_plan(
        run_id="run",
        round_id="round",
        logical_bytes=source.total_logical_bytes,
        max_working_bytes=1024 * 1024,
    )
    result = metadata_only_out_of_core_merge(plan=plan)
    event_log = tmp_path / "events.jsonl"
    event_log.write_text(
        '{"event_type":"metadata_only_merge","payload":{"payload_bytes":1000000000,'
        '"storage_kind":"metadata_only","checksum":"synthetic"}}\n',
        encoding="utf-8",
    )

    assert source.total_logical_bytes >= 1_000_000_000
    assert source.bytes_materialized == 0
    assert manifest.total_logical_bytes == source.total_logical_bytes
    assert result.simulation_only is True
    assert result.numeric_merge_performed is False
    assert event_log.stat().st_size < 5_000_000
