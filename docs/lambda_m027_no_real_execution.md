# Lambda M027 No Real Execution

M027 intentionally separates mutation-shaped request construction from real
Lambda execution.

Real execution is blocked by:
- execution context validation
- fake-server-only policy
- real Lambda URL rejection
- credential rejection
- response parser rejection of real API or billable-action claims
- semantic mutation audit coverage
- preflight reporting that real execution remains forbidden

The live Lambda client remains read-only. No real Lambda POST, PUT, PATCH, or
DELETE transport is introduced, and no CLI command can enable real launch or
termination.

The allowed M027 executable path is local fake-server execution only.

M028 keeps this restriction in place. It can authorize a future M029 attempt,
but it does not enable the M027 fake-server-only path against real Lambda.
