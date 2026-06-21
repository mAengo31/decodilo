# Lambda Teardown Audit

The M022 fake teardown audit validates that every synthetic fake Lambda resource
is terminal after teardown.

It checks:
- all fake resources are `terminated`
- failed terminate resources are reported
- fake orphan candidates are reported
- no live read-only resource was modified
- no executable real termination command was generated
- the journal contains terminate events
- lifecycle state and teardown counters agree

Failed audits set `manual_review_required=true`. The audit never terminates
real resources.
