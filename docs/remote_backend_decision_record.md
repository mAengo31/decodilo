# Remote Backend Decision Record

The decision record captures the review state for a future SDK addition.

Allowed statuses in Milestone 017:

- `rejected`
- `needs_more_evidence`
- `candidate_for_future_sdk_review`
- `blocked_by_risk`
- `blocked_by_missing_capability`
- `blocked_by_missing_evidence`

Forbidden statuses remain unavailable:

- `sdk_addition_allowed_by_policy`
- `real_backend_enabled`
- `launch_ready`
- `launch_allowed`

`candidate_for_future_sdk_review` means only that the evidence package is ready
for human review in a future milestone. It does not allow SDK addition or enable
any backend.
