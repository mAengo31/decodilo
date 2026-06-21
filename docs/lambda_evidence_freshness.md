# Lambda Evidence Freshness

M026 checks whether the evidence used for implementation authorization is still
recent enough for review.

Default freshness windows:
- live read-only discovery: 24 hours
- price snapshot: 7 days
- semantic mutation audit: 24 hours
- final prelaunch review: 24 hours

Stale or missing evidence can produce `needs_more_evidence`. A fresh read-only
Lambda discovery refresh may be run only through the existing read-only
`lambda live-discover` flow and only when explicitly available. Tests never
require live Lambda access.

Freshness checks do not launch, terminate, mutate, or spend.
