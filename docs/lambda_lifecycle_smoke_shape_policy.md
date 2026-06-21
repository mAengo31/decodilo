# Lambda Lifecycle Smoke Shape Policy

Lifecycle smoke tests should prefer the lowest-cost viable shape with a
Strand-compatible payload, existing SSH key selection, no filesystem
requirement, and a buffered 30-minute estimate under the approved budget.

After a capacity error, a same fixed-shape retry is blocked unless fresh
availability evidence changes or the operator explicitly accepts catalog-only
availability risk for a future review. Catalog-backed candidates are useful for
planning, but they are not live availability evidence.

M041 records that operator choice. Acceptance can authorize only a future M042
review; it cannot authorize immediate launch.
## M043 Capacity Rotation

Repeated capacity rejection for a lifecycle-smoke shape blocks silent same-shape
retry by default. M043 may rank alternative catalog-backed shapes under the
budget, but the result is only a future-review candidate. A later milestone must
collect fresh operator approval before any billable request.
