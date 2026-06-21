# Lambda Catalog Rotation Operator Decision

M044 records the operator decision after M043 selects a catalog-backed rotation
candidate. It supports three review-only outcomes:

- accept `gpu_8x_a100_80gb_sxm4` for a future M045 review
- decline the candidate and wait for live availability evidence
- decline the candidate and require manual catalog candidate selection

If the operator has not explicitly chosen one of those outcomes, M044 remains
`incomplete` and M045 is not authorized.

All artifacts keep `launch_ready=false`, `launch_allowed=false`,
`billable_action_performed=false`, and `real_mutation_enabled=false`.
