import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest
from decodilo.storage.memory_budget import MemoryBudget
from decodilo.storage.spill import SpillManager


def test_spill_to_disk_writes_reads_and_cleans_up(tmp_path) -> None:
    spill_dir = tmp_path / "spill"
    budget = MemoryBudget(
        max_in_memory_fragment_bytes=4,
        max_total_in_memory_bytes=4,
        spill_dir=spill_dir,
        allow_spill_to_disk=True,
        max_spill_bytes=100,
    )
    manager = SpillManager(budget=budget, run_id="run")

    manifest = manager.spill_bytes(
        artifact_id="spill-1",
        artifact_type="spill",
        data=b"large-payload",
        chunk_size_bytes=4,
    )

    assert manager.read_spill(manifest) == b"large-payload"
    assert budget.snapshot().current_spill_bytes == len(b"large-payload")
    manager.cleanup()
    assert not spill_dir.exists()


def test_retained_spill_files_can_be_included_in_artifact_manifest(tmp_path) -> None:
    spill_dir = tmp_path / "spill"
    budget = MemoryBudget(
        max_in_memory_fragment_bytes=4,
        max_total_in_memory_bytes=4,
        spill_dir=spill_dir,
        allow_spill_to_disk=True,
        max_spill_bytes=100,
    )
    manager = SpillManager(budget=budget, run_id="run")
    manager.spill_bytes(
        artifact_id="spill-retained",
        artifact_type="spill",
        data=b"large-payload",
        chunk_size_bytes=4,
    )
    manager.cleanup(retain=True)

    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in [run_spec, report, events]:
        path.write_text("{}", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
        spill_artifact_paths=manager.manifest_paths,
    )

    assert spill_dir.exists()
    assert [str(path) for path in manager.manifest_paths] == manifest.spill_artifact_paths
    assert all(manifest.artifacts[str(path)].exists for path in manager.manifest_paths)


def test_failed_spill_manifest_write_cleanup_removes_partial_files(tmp_path, monkeypatch) -> None:
    spill_dir = tmp_path / "spill"
    budget = MemoryBudget(
        max_in_memory_fragment_bytes=4,
        max_total_in_memory_bytes=4,
        spill_dir=spill_dir,
        allow_spill_to_disk=True,
        max_spill_bytes=100,
    )
    manager = SpillManager(budget=budget, run_id="run")

    def fail_replace(src, dst):  # noqa: ANN001
        raise RuntimeError("simulated manifest failure")

    monkeypatch.setattr("decodilo.storage.chunk_store.os.replace", fail_replace)
    with pytest.raises(RuntimeError, match="simulated"):
        manager.spill_bytes(
            artifact_id="spill-failed",
            artifact_type="spill",
            data=b"large-payload",
            chunk_size_bytes=4,
        )

    manager.cleanup()
    assert not spill_dir.exists()
