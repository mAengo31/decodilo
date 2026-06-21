# Lambda Capacity History Selector Policy

The M044H selector policy is conservative by default:

- `exclude_recent_capacity_failures=true`
- `require_fresh_live_availability_for_same_shape_retry=true`
- `allow_same_shape_retry_with_explicit_acceptance=false`
- `max_budget=50`
- `max_runtime_minutes=30`
- `quantity=1`
- `prefer_single_gpu=true`
- `prefer_lowest_cost=true`
- `no_auto_retry=true`

Enabling same-shape retry for a recent capacity failure requires a separate
operator acceptance artifact and still only authorizes future review. It never
sets `launch_ready=true` or `launch_allowed=true`.

M045 approval for a capacity-history-selected alternative does not weaken this
policy. It can approve only the selector-chosen alternative for a future review;
same-shape retry remains separately gated.
