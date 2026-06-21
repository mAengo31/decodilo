# Lambda M051 One-Shot Arming

M051A adds an ephemeral arming chain for the metadata-only bootstrap path.
Standing M050/M051 review artifacts remain durable and non-executable:

- `launch_ready=false`
- `launch_allowed=false`
- `launch_authorized_now=false`

The one-shot arming artifact binds operator confirmation, the metadata plan,
the execution gate, the no-mutation/no-SSH audit, bootstrap authorization, and
response-loss controls by hash. It is scoped to
`m051_metadata_only_single_launch_attempt`, `max_launch_attempts=1`, no automatic
retry, no SSH, no remote commands, no package install, and no training.

`one_shot_request_send_permitted` is intentionally `false` on the arming artifact.
Only the reviewer bridge may expose that field as `true`.
