from __future__ import annotations

from lambda_m046a_helpers import run_m046_fake


def test_m046_capacity_selected_missing_artifact_blocks_before_request(tmp_path):
    result = run_m046_fake(
        tmp_path,
        omit={"--capacity-aware-selector-output"},
    )

    assert result.returncode != 0
    assert "requires all capacity-selected artifacts" in result.stderr
    assert not (result.workdir / "journal.jsonl").exists()  # type: ignore[attr-defined]
    assert not (result.workdir / "report.json").exists()  # type: ignore[attr-defined]
