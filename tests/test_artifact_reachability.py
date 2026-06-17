import json

import pytest

from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.reachability import build_reachability_graph

pytestmark = [pytest.mark.unit, pytest.mark.storage]


def test_reachability_protects_recovery_checkpoint(tmp_path) -> None:
    checkpoint = tmp_path / "syncer_checkpoint.json"
    checkpoint.write_text("checkpoint\n", encoding="utf-8")
    (tmp_path / "run_spec.json").write_text('{"run_id":"run-gc"}\n', encoding="utf-8")
    (tmp_path / "report.json").write_text('{"run_id":"run-gc","metrics":{}}\n', encoding="utf-8")
    (tmp_path / "recovery_manifest.json").write_text(
        json.dumps(
            {
                "checkpoint_ref": {"path": str(checkpoint)},
                "required_artifact_hashes": {},
            }
        ),
        encoding="utf-8",
    )

    index = build_artifact_index(tmp_path)
    graph = build_reachability_graph(workdir=tmp_path, index=index)

    assert str(checkpoint) in graph.protected

