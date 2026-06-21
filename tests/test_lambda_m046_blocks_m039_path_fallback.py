from __future__ import annotations

from lambda_m046a_helpers import run_m046_fake


def test_m046_capacity_selected_flags_block_m039_fallback(tmp_path):
    result = run_m046_fake(tmp_path, include_m039_args=True)

    assert result.returncode != 0
    assert "cannot be combined with M039 lower-cost gates" in result.stderr
    assert not (result.workdir / "journal.jsonl").exists()  # type: ignore[attr-defined]
