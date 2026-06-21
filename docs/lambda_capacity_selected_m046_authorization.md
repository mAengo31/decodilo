# Lambda Capacity-Selected M046 Authorization

The M046 authorization package is future-only. It can be produced only after:

- the capacity-selected cost/risk review passes
- operator approval is complete
- capacity-history selector authorization passed
- capacity-history selector gate-check passed
- response-loss controls passed
- existing SSH key selection is present
- non-sample price evidence is used
- automatic launch retry remains disabled

The authorization status
`authorized_for_future_m046_capacity_selected_launch_review` allows only a
future supervised review milestone. It must not set `launch_ready=true`,
`launch_allowed=true`, `execute_now`, or `real_mutation_enabled=true`.

The real execution path must consume this authorization through the explicit
M046 capacity-selected `lambda m029 run` flags. If any M046 flag is present, the
command must require the full M046 artifact set and must not fall back to older
M028/M029 or M039 lower-cost artifact handling.
