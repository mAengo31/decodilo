# Lambda Minimal Mutation Path

Milestone 027 adds the minimal mutation-shaped code path needed to prepare and
exercise future Lambda launch and termination requests against a local fake
server only.

This is not a real Lambda launch path. The implementation can construct
reviewed request models for:
- `launch_one_instance`
- `terminate_owned_instance`

Execution is allowed only when the execution context is
`fake_server_only`, the target is localhost or an in-memory fake transport, and
all M027 evidence gates are present.

Required evidence includes:
- M027 implementation authorization
- operation spec
- budget lock
- idempotency plan
- resource scope
- teardown plan
- termination verification policy evidence
- endpoint policy enabled
- mutation guard enabled
- no real credentials
- no real Lambda URL

All reports retain `real_mutation_enabled=false`, `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false`.

M028 does not broaden this path. The M027 minimal mutation executor remains
fake-server-only, even when M028 produces a next-milestone M029 authorization
package.
