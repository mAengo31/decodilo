# Lambda Read-Only Discovery

M018 discovery uses fixture data or the local fake transport. Discovery reports
include:
- regions
- instance types
- images
- SSH keys
- filesystems
- running fixture instances
- quota
- usage estimates

Every discovery report has `live_api_used=false`. Availability, quota, and
billing models built from these reports are planning estimates only and do not
prove real Lambda capacity, real quota, or live billing state.

M019 adds a separate live read-only discovery report where `live_api_used=true`
is allowed. That report must also include `read_only_mode=true`,
`mutation_guard_enabled=true`, `endpoint_policy_enabled=true`, and
`billable_action_performed=false`.

M019A extends the live report with endpoint calibration, response-shape drift,
pagination evidence, redaction mode, and unmanaged-resource summary fields.
