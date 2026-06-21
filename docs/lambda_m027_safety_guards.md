# Lambda M027 Safety Guards

M027 adds a stricter execution context and policy around the minimal mutation
path.

Fake execution requires:
- M027 authorization for implementation only
- `fake_server_only` mode
- localhost or in-memory fake target
- endpoint policy enabled
- mutation guard enabled
- budget lock within first-launch policy limits
- idempotency plan
- owned resource scope
- teardown plan
- termination verification policy evidence
- no unmanaged billable resources
- no real Lambda URL
- no real credentials

The policy can allow fake execution, but it always keeps real execution
forbidden. Reports continue to emit `real_execution_allowed=false`,
`real_mutation_enabled=false`, `launch_ready=false`, and
`launch_allowed=false`.

