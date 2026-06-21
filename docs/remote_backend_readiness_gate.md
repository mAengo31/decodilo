# Remote Backend Readiness Gate

Milestone 016 defines the evidence required before a future milestone may even
consider adding a real remote artifact backend SDK.

Allowed current statuses are `not_started`, `evidence_missing`,
`simulation_only`, `conformance_failed`, `conformance_passed_simulator_only`,
and `implementation_review_required`.

Future enum values for `sdk_addition_allowed_by_policy` and
`real_backend_enabled` are reserved, but Milestone 016 code cannot emit them.

Required evidence includes learner scaling, backend design targets, remote
requirements, design validation, conformance, security, credential/auth,
encryption, integrity, idempotency, lifecycle, replay/restore, cost, bandwidth,
and preflight reports, plus proof that no raw secrets, SDK dependency, network
requirement, remote backend enablement, or cloud launch path has appeared.

Passing simulator conformance is not production backend readiness. It only
supports implementation review.

Milestone 017 consumes this readiness report to build a review-only proposal and
decision record. The highest resulting decision remains
`candidate_for_future_sdk_review`.
