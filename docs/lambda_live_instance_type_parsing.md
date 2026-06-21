# Lambda Live Instance-Type Parsing

Lambda `/instance-types` may return a map-shaped response keyed by instance type or a
list-shaped response. M047 makes both forms first-class through
`lambda live-instance-types parse`.

The parser extracts the canonical instance type id, GPU description, price per hour, live
available regions, and unknown raw fields. A candidate is live-available only when its
available-region list is non-empty.

Selectors and future launch gates should consume parsed live instance-type evidence
instead of relying on stale catalog-only shape names.
