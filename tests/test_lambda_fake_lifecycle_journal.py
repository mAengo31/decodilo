import json

from decodilo.lambda_cloud.fake_lifecycle_journal import FakeLambdaLifecycleJournal


def test_fake_lifecycle_journal_replay_reconstructs_state(tmp_path) -> None:
    journal = FakeLambdaLifecycleJournal(tmp_path / "journal.jsonl", lifecycle_id="life")
    journal.append("fake_launch_requested", idempotency_key="idem")
    journal.append(
        "fake_launch_started",
        resource_id="fake-i-life-0",
        idempotency_key="idem",
        payload={"launch_plan_node_id": "node-0"},
    )
    journal.append("fake_instance_running", resource_id="fake-i-life-0")
    journal.append("fake_health_check_passed", resource_id="fake-i-life-0")

    replay = journal.replay()

    assert replay.passed is True
    assert replay.state.resources["fake-i-life-0"].state == "healthy"
    assert replay.state.real_lambda_api_used is False


def test_fake_lifecycle_journal_rejects_corrupted_event(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")
    journal = FakeLambdaLifecycleJournal(path, lifecycle_id="life")

    replay = journal.replay()

    assert replay.passed is False
    assert "corrupted fake lifecycle event" in replay.errors[0]


def test_fake_lifecycle_journal_rejects_missing_event(tmp_path) -> None:
    journal = FakeLambdaLifecycleJournal(tmp_path / "journal.jsonl", lifecycle_id="life")
    event = journal.append("fake_launch_requested")
    payload = json.loads(event.stable_json())
    payload["event_id"] = "fake-evt-000003"
    journal.path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    replay = journal.replay()

    assert replay.passed is False
    assert "out-of-order" in replay.errors[0]


def test_fake_lifecycle_journal_contains_fake_only_flags(tmp_path) -> None:
    journal = FakeLambdaLifecycleJournal(tmp_path / "journal.jsonl", lifecycle_id="life")
    event = journal.append("fake_launch_requested")
    payload = json.loads(event.stable_json())

    assert payload["fake_only"] is True
    assert payload["real_lambda_api_used"] is False
    assert payload["billable_action_performed"] is False


def test_fake_lifecycle_journal_rejects_real_api_flag(tmp_path) -> None:
    journal = FakeLambdaLifecycleJournal(tmp_path / "journal.jsonl", lifecycle_id="life")
    event = journal.append("fake_launch_requested")
    payload = json.loads(event.stable_json())
    payload["real_lambda_api_used"] = True
    journal.path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    replay = journal.replay()

    assert replay.passed is False
    assert "fake-only invariants" in replay.errors[0]
