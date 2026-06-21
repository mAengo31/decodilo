# Lambda Operator Checklist

The M025 operator checklist captures human acknowledgements for a future first
Lambda launch review.

The operator must acknowledge billable-resource risk, Lambda-level termination
verification, the 50 USD budget limit, 30-minute runtime limit, one-instance
scope, no training workload, no SSH/setup scripts without later review,
operator availability, disabled launch in M025, resource-ledger review,
teardown runbook review, and kill-switch design review.

Checklist completion is review-only. It cannot enable launch or mutation.

M026 adds a separate human review manifest with stricter acknowledgements for
M027 implementation authorization. Both artifacts remain review-only.

M028 adds a final operator confirmation package. Complete acknowledgement can
support only next-milestone M029 authorization; it still cannot enable launch in
the M028 build.
