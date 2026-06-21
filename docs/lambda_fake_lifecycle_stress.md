# Lambda Fake Lifecycle Stress

M022 stress runs repeat fake launch and teardown cycles through deterministic
idempotency keys and failure modes.

Stress cycles check:
- journal replay
- fake mutation contract
- teardown verification
- orphan detection
- manual-review signals

Supported local failure modes include:
- `none`
- `duplicate_launch_request`
- `fail_after_launch_before_health`
- `partial_terminate_failure`
- `terminate_timeout`

Stress reports are evidence only. They keep `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false`.
