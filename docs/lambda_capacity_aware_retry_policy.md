# Lambda Capacity-Aware Retry Policy

Capacity-aware retry policy separates capacity rejection from response loss.

Rules:

- no automatic retry after any capacity rejection
- no same-shape future review without fresh live availability evidence or an
  explicit future operator decision
- catalog candidate rotation may be prepared for a future review
- live availability refreshes remain read-only

The policy is intentionally conservative because the provider can reject a
catalog-backed shape even when it remains listed in product data.

M043 policy artifacts are advisory and review-only. They must keep
`launch_ready=false`, `launch_allowed=false`, `billable_action_performed=false`,
and `real_mutation_enabled=false`.

M044 may use this policy to authorize only a future catalog-rotation review for
an alternative candidate. Same-shape retry remains blocked unless fresh live
availability evidence changes the policy input.
