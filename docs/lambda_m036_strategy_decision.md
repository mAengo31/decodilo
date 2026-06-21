# Lambda M036 Strategy Decision

M036 decides only the next review path after support/operator endpoint
confirmation is requested or ingested.

Allowed decisions are:

- `require_more_support_evidence`
- `endpoint_confirmed_proceed_to_reauthorization`
- `reauthorize_lower_cost_shape_before_next_launch`
- `keep_current_shape_with_operator_risk_acceptance`
- `pause_real_launch_attempts`

Forbidden outcomes include `launch_now`, `execute_now`, `launch_ready=true`, and
`launch_allowed=true`.

If support evidence is missing or incomplete, M036 records
`require_more_support_evidence`. If endpoint confidence upgrades to high and a
lower-cost lifecycle smoke shape is recommended, M036 records that future shape
reauthorization is the next step.
