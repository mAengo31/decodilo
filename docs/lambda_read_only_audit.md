# Lambda Read-Only Audit

The read-only audit report verifies that every live Lambda request was:

- GET
- endpoint-policy allowlisted
- mutation-free
- sent without a request body
- secret-redacted

The audit fails if it sees launch, terminate, restart, create, delete, a denied
endpoint attempt, a request body, or a secret-like value. The audit also records
`billable_action_performed=false`, `launch_ready=false`, and
`launch_allowed=false`.

M019A adds an explicit audit status:
- `passed`: all observed requests were successful read-only calls.
- `passed_with_read_failures`: requests were still read-only, but one or more
  endpoint reads returned an error or non-2xx status.
- `failed`: a mutation, non-GET request, request body, denied endpoint attempt,
  billable action, or secret-like value was observed.

M019C classifies quota and usage 404s as `unsupported_optional_endpoint` for
the standard endpoint set. Those optional read failures can result in
`passed_with_read_failures`, but they do not indicate mutation or spend.
