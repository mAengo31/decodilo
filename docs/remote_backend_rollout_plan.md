# Remote Backend Rollout Plan

Milestone 017 defines future rollout phases but implements none of them.

Current phase:

- `phase_0_design_only`

Future planned phases:

- SDK import only, disabled
- fake credentials with no network
- read-only metadata discovery
- sandbox writes
- single-node artifact smoke
- multi-learner artifact smoke
- budgeted scale test

Every future phase requires manual approval and keeps
`remote_backend_enabled=false` until a later explicit milestone changes policy.
