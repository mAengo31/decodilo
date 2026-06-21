# Lambda Flexible Selector Operator Approval

Flexible selector approval acknowledges that the selector may choose any
currently available approved shape satisfying the lifecycle-smoke policy. The
operator must also acknowledge that catalog-only candidates do not prove live
availability.

Approval may only produce:

- `approved_for_future_flexible_selector_launch_review`
- `declined_wait_for_live_availability`
- `not_provided`

It must never produce immediate launch authorization. A future real launch
milestone still requires fresh gates, tests, read-only discovery, and explicit
operator presence.
