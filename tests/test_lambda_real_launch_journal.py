from pathlib import Path

from decodilo.lambda_cloud.real_launch_journal import (
    LambdaM029LaunchJournal,
    replay_m029_launch_journal,
)


def test_real_launch_journal_replay_and_corruption(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal = LambdaM029LaunchJournal(path, run_id="run")
    journal.append("m029_owned_instance_recorded", metadata={"owned_instance_id": "fake-i-1"})
    journal.append("m029_readonly_verify_terminated", metadata={"termination_verified": True})

    replay = replay_m029_launch_journal(path)

    assert replay.replay_passed is True
    assert replay.owned_instance_id == "fake-i-1"
    assert replay.termination_verified is True

    bad = Path(tmp_path / "bad.jsonl")
    bad.write_text("{not-json}\n", encoding="utf-8")
    assert replay_m029_launch_journal(bad).corrupted is True
