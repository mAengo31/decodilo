import json

from decodilo.lambda_cloud.fake_lifecycle_journal import FakeLambdaLifecycleJournal


def test_journal_tamper_rejected_for_non_fake_event(tmp_path) -> None:
    journal = FakeLambdaLifecycleJournal(tmp_path / "journal.jsonl", lifecycle_id="life")
    event = journal.append("fake_launch_requested")
    payload = json.loads(event.stable_json())
    payload["billable_action_performed"] = True
    journal.path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    replay = journal.replay()

    assert replay.passed is False
    assert "fake-only invariants" in replay.errors[0]
