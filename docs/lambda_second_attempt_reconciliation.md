# Lambda Second Attempt Reconciliation

The second-attempt reconciliation plan defines how a future M031 run must
decide whether a launched resource is owned and whether termination is safe.

Rules:

- use the launch response owned instance ID when present
- use read-only discovery after launch success
- use read-only discovery after timeout or response loss
- do not terminate low-confidence or unknown candidates
- require manual console review for ambiguity
- verify termination through Lambda read-only get/list
- reconcile the final ledger and journal

OS shutdown is not termination, and unowned instances must never be terminated.
