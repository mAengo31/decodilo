# Lambda SSH Retry Operator Decision

M055D can produce one of these decision states:

- `authorize_future_live_candidate_ssh_retry_review`
- `wait_for_fresh_live_availability`
- `pause_ssh_work`
- `needs_more_evidence`

It must never produce `launch_now`, `ssh_now`, `launch_ready`,
`launch_allowed`, or `run_command_now`.

When live candidate selection passes and retry policy passes, M055D may
authorize only a future M056 review. The future M056 run still needs fresh
operator confirmation, fresh read-only discovery, one-shot arming, and teardown
verification.
