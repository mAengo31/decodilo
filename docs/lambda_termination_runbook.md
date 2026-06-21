# Lambda Termination Runbook

The M025 termination runbook is non-executable and exists to define future
verification requirements.

Future termination must use the owned instance ID from the launch ledger,
target only that owned ID, verify terminal state through read-only Lambda
list/get calls, reconcile the ledger, collect audit artifacts, and trigger
manual review on timeout, malformed responses, unavailable read endpoints, or
unknown state.

OS shutdown is insufficient evidence of cloud resource termination. M025 adds no
real terminate command.

M028 finalizes this into a non-executable teardown verification plan for M029:
owned instance only, read-only verification, timeout escalation, final
ledger/audit collection, and billable-action evidence collection.
