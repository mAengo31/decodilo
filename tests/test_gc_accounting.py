import pytest

from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.gc_accounting import build_gc_accounting_report
from decodilo.storage.reachability import build_reachability_graph

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def test_gc_accounting_has_disjoint_reachability_partition(tmp_path) -> None:
    (tmp_path / "run_spec.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "report.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "orphan.tmp").write_text("orphan\n", encoding="utf-8")

    index = build_artifact_index(tmp_path)
    graph = build_reachability_graph(workdir=tmp_path, index=index, allow_incomplete=True)
    report = build_gc_accounting_report(index=index, graph=graph)

    assert report.disjoint_partition_valid is True
    assert (
        report.reachable_count + report.unreachable_count + report.unresolved_count
        == report.unique_artifacts_scanned
    )
    assert report.protected_count <= report.unique_artifacts_scanned
    assert report.overlaps_explained


def test_gc_accounting_represents_confusing_overlap_unambiguously(tmp_path) -> None:
    (tmp_path / "run_spec.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "report.json").write_text("{}\n", encoding="utf-8")
    for index in range(3):
        (tmp_path / f"temp-{index}.tmp").write_text("temp\n", encoding="utf-8")

    artifact_index = build_artifact_index(tmp_path)
    graph = build_reachability_graph(
        workdir=tmp_path,
        index=artifact_index,
        allow_incomplete=True,
    )
    report = build_gc_accounting_report(index=artifact_index, graph=graph)

    assert report.artifacts_scanned_total == report.unique_artifacts_scanned
    assert report.temporary_count == 3
    assert "protection_state is an overlay" in report.overlaps_explained[0]

