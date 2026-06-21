# Lambda Endpoint Calibration

Endpoint calibration records what each read-only Lambda endpoint did during a
fake or live-read-only discovery run.

Each endpoint result records:
- operation and GET endpoint path
- endpoint-policy and mutation-guard decisions
- attempt/success status and HTTP status code when available
- response shape summary and item count
- unknown fields seen in parsed fixture/live models
- pagination evidence
- redacted error type/message
- `mutation=false`
- `billable_action_performed=false`

Discovery endpoint sets are:
- `minimal`: instance types and instances
- `standard`: instance types, regions, images, SSH keys, filesystems,
  instances, quota, and usage when endpoints are available
- `extended`: currently the standard allowlist, reserved for additional
  explicitly read-only endpoints

Pagination helpers support non-paginated responses plus common fixture
patterns such as `next_token`, `next`, and `page`/`total_pages`. They enforce
`max_pages` and `max_items` and reject repeated-token loops.

Endpoint results distinguish required and optional reads. For the standard
set, `list_instance_types` and `list_instances` must succeed for
`required_endpoint_success=true`. Regions, images, SSH keys, filesystems,
quota, and usage are optional. Unsupported optional endpoints, such as quota or
usage returning 404, are counted separately from schema validation failures:
`endpoint_count_unsupported_optional` increments and
`optional_endpoint_warnings` records the endpoint.

Unknown fields are schema-drift evidence, not fatal by default. Public
summaries redact resource IDs; local private reports may keep resource IDs for
ledger reconciliation but still redact API keys, authorization headers, bearer
tokens, and secret-like values.
