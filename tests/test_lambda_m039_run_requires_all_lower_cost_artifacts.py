from __future__ import annotations

from lambda_m039a_helpers import run_m039_fake


def test_m039_lower_cost_run_missing_artifact_blocks_before_request(tmp_path):
    result = run_m039_fake(tmp_path, omit={"--ssh-key-selection"})

    assert result.returncode != 0
    assert "requires all lower-cost artifacts" in result.stderr
    assert not (result.workdir / "journal.jsonl").exists()  # type: ignore[attr-defined]
    assert not (result.workdir / "report.json").exists()  # type: ignore[attr-defined]
