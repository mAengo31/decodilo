import json

import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.syncer_checkpoint import load_syncer_checkpoint
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig


def test_syncer_writes_and_loads_checkpoint(tmp_path) -> None:
    service = SyncerService(SyncerServiceConfig(run_id="run-syncer-cp", workdir=tmp_path))

    service._write_syncer_checkpoint()
    checkpoint = load_syncer_checkpoint(tmp_path / "syncer_checkpoint.json")

    assert checkpoint.run_id == "run-syncer-cp"
    assert checkpoint.global_version == 0
    assert checkpoint.idempotency_table == {}


def test_corrupted_syncer_checkpoint_is_rejected(tmp_path) -> None:
    service = SyncerService(SyncerServiceConfig(run_id="run-syncer-cp", workdir=tmp_path))
    service._write_syncer_checkpoint()
    path = tmp_path / "syncer_checkpoint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["global_version"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(InvariantViolation, match="checksum"):
        load_syncer_checkpoint(path)
