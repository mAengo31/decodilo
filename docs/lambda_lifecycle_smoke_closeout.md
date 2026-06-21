# Lambda Lifecycle Smoke Closeout

Lifecycle smoke closeout combines the success record, post-run reconciliation, and
evidence package.

`closed_success` or `closed_with_warnings` is allowed only when the owned instance was
terminated, final read-only discovery shows no visible or unmanaged instances, the
evidence package is complete, and no secret leakage was detected. Optional read-only
endpoint warnings may downgrade the status to warnings without making the closeout
unresolved.

Any visible running instance, unmanaged resource, missing termination verification, or
missing core evidence leaves the closeout unresolved.
