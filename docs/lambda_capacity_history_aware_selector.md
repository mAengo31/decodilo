# Lambda Capacity History Aware Selector

M044H adds capacity history to the flexible availability-first selector. The
selector remains review-only and cannot launch, terminate, mutate Lambda
resources, or authorize immediate execution.

Inputs:

- capacity history
- capacity retry policy
- non-sample price snapshot
- existing SSH key selection
- Strand response-loss controls
- latest read-only discovery, when available
- optional same-shape capacity retry acceptance

Default rules:

- Exclude shapes with recent confirmed capacity errors.
- Treat a shape as recently capacity-failed when the same shape has a confirmed
  capacity error and no fresh live availability evidence proves it is available
  now.
- Exclude `gpu_1x_h100_pcie` by default after the M039B and M042 capacity
  errors.
- Do not let generic catalog-only risk acceptance override recent capacity
  history.
- Require a separate same-shape capacity retry acceptance artifact before a
  recently capacity-failed same-shape retry can be reviewed.
- If every eligible candidate is excluded, return `no_candidate` and recommend
  waiting for live availability.

Candidate ranking still prefers live availability first, then lower buffered
30-minute cost, fewer GPUs, no filesystem requirement, and Strand-compatible
payloads.

All artifacts keep `launch_ready=false`, `launch_allowed=false`,
`billable_action_performed=false`, and `real_mutation_enabled=false`.

M045 consumes the capacity-history-aware selector output to collect explicit
operator approval for the selected candidate and produce a future M046 review
package. M045 does not alter selector ranking and does not launch.
## M047 Live Shape Handling

Capacity-history-aware selection must exclude recent capacity failures by default and use
the canonical live shape id emitted by the live instance-type parser. Stale shape ids are
not valid launch artifacts unless an explicit alias-resolution report maps them to a
live `/instance-types` id.
