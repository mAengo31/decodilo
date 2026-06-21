# Lambda Availability-First Selector

The availability-first selector wraps candidate extraction and ranking for
future Lambda lifecycle-smoke reviews.

Inputs:

- read-only discovery report
- non-sample price snapshot
- existing SSH key selection
- maximum budget

Outputs:

- ranked candidates
- selected candidate if one is viable
- why the selected candidate won
- whether the candidate is live-available or catalog-only
- whether operator risk acceptance is required
- whether the selected candidate is launch-selectable without catalog-only risk
  acceptance

The selector is review-only. It must not call mutation endpoints, retry launch,
create resources, or authorize immediate execution.

The selector must not preselect a fixed GPU shape. It may choose any approved
Lambda shape that is represented by non-sample price evidence, has buffered
30-minute cost below budget, can be launched as a quantity-1 Strand-compatible
payload with an existing SSH key, requires no filesystem, uses no SSH, setup
script, cloud-init, or training path, disables automatic retry, and requires
owned-instance termination if an instance is created.

Ranking order:

1. live availability
2. lowest buffered 30-minute cost
3. single-GPU preference
4. no filesystem requirement
5. Strand-compatible payload

If no live-available candidate exists, the selector may identify the best
catalog-only candidate, but `launch_selection_allowed=false` until the operator
explicitly accepts catalog-only availability risk.

M041 consumes the selector output when the selected candidate is catalog-only.
The operator must either accept the catalog-only risk for a future M042 review
or decline it and wait for live availability evidence. The selector itself does
not make that operator decision.

M043 consumes repeated capacity closeouts and excludes recently failed shapes by
default before ranking alternative catalog candidates. These alternatives remain
catalog-backed rather than live-availability-backed until a future read-only
source proves otherwise.

M044G consumes flexible selector output directly. Future flexible-selector
launch review artifacts must use selector output as the selected-shape source
and must not fall back to hardcoded lower-cost or catalog-rotation shapes.

M044H makes the flexible selector capacity-history-aware. Recent
capacity-failed shapes are excluded by default unless fresh live availability
evidence proves the shape is available now. Generic catalog-only risk
acceptance does not override recent capacity history; same-shape retry requires
a separate same-shape capacity retry acceptance artifact for future review.
## M047 Live Catalog Contract

Availability-first selection must consume canonical live Lambda shape ids from parsed
`/instance-types` evidence when live data is available. Catalog-only evidence may rank
candidates, but it must not override live availability, live-region selection, or stale
shape alias resolution.
