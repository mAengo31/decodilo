# Lambda Availability-First Launch Review

Availability-first review ranks lifecycle-smoke candidates before any future
launch attempt. The selector uses:

- live read-only instance-type evidence when available
- non-sample catalog price evidence
- existing SSH key selection
- Strand-compatible payload constraints
- response-loss controls from the lower-cost path

If the live instance-type endpoint returns no useful candidates, M040 records
`endpoint_inconclusive` instead of inventing capacity. Catalog-only candidates
may still be ranked for planning, but they require future operator risk
acceptance because catalog price is not live capacity.

M040 authorization is future-review only. It keeps `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false`.
