# Lambda Remote Bootstrap Strategy

After a successful metadata-only bootstrap, repeating the same metadata-only run
is not the default next step. The strategy update recommends planning a future
SSH-connectivity-only review if the operator wants remote access.

That recommendation is planning-only. It does not approve SSH now, command
execution now, package installation, training, or launch. Training remains
explicitly denied.

If metadata bootstrap closeout is unresolved, the strategy status becomes
`needs_more_evidence`.

M053 turns `ssh_connectivity_planning` into explicit review artifacts: scope,
credential policy, client policy, no-command policy, no-transfer policy,
no-forwarding policy, risk review, future M054 authorization, and a non-executable
runbook preview. Without explicit operator approval, the M054 authorization remains
`not_authorized`.
