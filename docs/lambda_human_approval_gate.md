# Lambda Human Approval Gate

M020 introduces a human approval manifest and gate for future Lambda lifecycle
work. The approval manifest records operator acknowledgements and approved
limits for a future fake launch lifecycle review.

Required acknowledgements cover:
- billable actions
- termination requirements
- budget limits
- no background work
- no production training
- launch is not enabled yet

Allowed M020 approval statuses are:
- `not_requested`
- `incomplete`
- `approved_for_future_fake_launch_lifecycle`
- `rejected`

`approved_for_future_real_launch_review` is intentionally rejected in M020.
Even a complete approval manifest does not enable launch. Approval reports keep
`launch_ready=false` and `launch_allowed=false`.

M021 adds an `approval-template --approve-fake-lifecycle` helper. It can produce
`approved_for_future_fake_launch_lifecycle` when all acknowledgements are true
and limits remain within policy. It cannot produce real-launch approval and
still keeps `launch_ready=false` and `launch_allowed=false`.

M023 remains review-only. Human approval evidence can be referenced by the real
mutation boundary proposal and evidence package, but no approval status may
enable real mutation or launch.
