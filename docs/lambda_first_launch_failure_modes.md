# Lambda First Launch Failure Modes

M023 records a failure-mode table for future first real launch review. The table
is not executable recovery logic.

Covered modes include lost launch response, launch timeout with an instance
created, malformed launch response, stuck pending instance, running instance
with unknown health, lost terminate response, terminate timeout, unknown
termination state, unavailable read-only verification endpoint, budget threshold
exceeded, local crash after launch, corrupted ledger, approval mismatch, wrong
instance type, wrong region, duplicate launch request, and duplicate terminate
request.

Each mode records detection, mitigation, required evidence, manual review
trigger, and residual risk. Unknown or non-terminal state requires human review.
