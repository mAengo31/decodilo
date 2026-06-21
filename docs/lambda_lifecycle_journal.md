# Lambda Lifecycle Journal

M021 uses a JSONL journal for fake Lambda lifecycle events. Each event is sorted
JSON and includes fake-only invariants:
- `fake_only=true`
- `real_lambda_api_used=false`
- `billable_action_performed=false`

Event IDs are deterministic within a journal, for example
`fake-evt-000001`. Replay rejects corrupted JSON, missing/out-of-order events,
and any event that violates fake-only flags.

Replay reconstructs the fake lifecycle state after process-style interruptions.
This is used to test idempotent fake launch requests, duplicate teardown
requests, and crash recovery without creating cloud resources.
