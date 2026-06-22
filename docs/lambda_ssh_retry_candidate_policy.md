# Lambda SSH Retry Candidate Policy

M055D retry policy is future-review only. It forbids automatic retry after
capacity rejection, response loss, malformed response, or SSH failure.

A future M056 SSH diagnostic retry must use:

- one launch attempt only,
- one SSH authentication probe only,
- explicit `ubuntu`,
- `IdentitiesOnly=yes`,
- isolated known-hosts handling,
- bounded redacted stderr capture,
- no remote command,
- no file transfer,
- no port forwarding,
- no package installation,
- no training.

The policy keeps `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.
