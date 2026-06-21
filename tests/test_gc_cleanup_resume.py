import pytest

from decodilo.storage.gc_cleanup import cleanup_gc_trash

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def test_gc_cleanup_skips_failed_transaction_by_default(tmp_path) -> None:
    tx_root = tmp_path / ".decodilo_gc_transactions"
    trash = tmp_path / ".decodilo_trash" / "gc-failed"
    tx_root.mkdir()
    trash.mkdir(parents=True)
    (trash / "payload").write_text("staged\n", encoding="utf-8")
    (tx_root / "gc-failed.json").write_text(
        """
{
  "transaction_id": "gc-failed",
  "run_id": "run",
  "schema_version": "v1",
  "planned_deletes": [],
  "pre_delete_hashes": {},
  "delete_started_at": null,
  "delete_completed_at": null,
  "deleted_paths": [],
  "failed_deletes": {"payload": "boom"},
  "skipped_protected": [],
  "rollback_possible": true,
  "transaction_state": "failed",
  "trash_dir": null
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = cleanup_gc_trash(workdir=tmp_path, apply=True)

    assert report.skipped_failed_transactions == ["gc-failed"]
    assert trash.exists()
