# Lambda Flexible Selector Authorization

M044G replaces fixed-shape future launch review with selector-driven review.
The selected shape must come from the flexible availability-first selector
output, not from hardcoded M039/M045 artifacts.

M044H extends this rule with capacity history. Authorization must consume the
capacity-history-aware selector output when capacity history exists. A recent
capacity-failed candidate cannot be authorized through generic catalog-only
risk acceptance; it requires either fresh live availability evidence or a
separate same-shape capacity retry acceptance artifact.

Authorization is future-only. It requires:

- selector output with `launch_selection_allowed=true`
- complete operator approval for flexible selector review
- existing SSH key selection
- Strand response-loss controls
- quantity `1`
- buffered 30-minute cost below `$50`
- Strand-compatible payload
- no filesystem requirement
- no automatic launch retry
- owned-instance termination required if an instance is created
- no recent capacity failure for the selected candidate, unless explicitly
  accepted through the same-shape capacity retry path

All authorization artifacts keep `launch_ready=false`,
`launch_allowed=false`, `billable_action_performed=false`, and
`real_mutation_enabled=false`.
