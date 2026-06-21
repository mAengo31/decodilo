# Lambda Lower-Cost M039 Authorization

The lower-cost M039 authorization record is future-only. It can emit
`authorized_for_future_m039_lower_cost_launch_attempt` only when readiness,
state snapshot, budget lock, resource lock, launch-window lock, response-loss
controls, and operator approval all pass.

The record must not emit `launch_now`, `execute_now`, `launch_ready=true`, or
`launch_allowed=true`.

After M038A operator approval is complete, the authorization may pass as
`authorized_for_future_m039_lower_cost_launch_attempt` with
`launch_authorized_for_next_milestone=true` and `launch_authorized_now=false`.
It carries the selected shape, selected SSH key hash, and 30 minute cost
estimate for audit, but it still cannot execute a launch.
