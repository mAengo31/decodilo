# Lambda Launch Blockers

M020 aggregates planning blockers into a launch blocker report and readiness
summary.

Blocker categories include:
- missing live discovery
- missing read-only audit
- missing price or resource reconciliation
- missing teardown plan
- missing budget manifest
- missing human approval
- unmanaged billable resources
- sample or stale pricing
- shape not discovered
- missing price
- budget exceeded
- runtime too long
- too many instances
- remote backend not ready
- launch code disabled
- launch not supported in current milestone

`future_fake_launch_lifecycle_candidate` may become true when all M020 planning
evidence is complete except invariant blockers such as disabled launch code and
remote backend readiness. `future_real_launch_candidate` remains false in M020.

The readiness summary always keeps `launch_ready=false` and
`launch_allowed=false`.

M021 keeps `launch_not_supported_in_current_milestone` as a real-launch blocker
even when fake lifecycle rehearsal passes. Fake lifecycle success may clear
local rehearsal blockers, but `future_real_launch_candidate=false` remains the
required outcome.

M023 adds design-review artifacts, but launch remains blocked by absence of real
mutation implementation, disabled transport spec, arming-gate design-only
status, and current-milestone policy. `design_review_ready` is not a launch
status.
