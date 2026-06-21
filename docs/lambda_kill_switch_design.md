# Lambda Kill-Switch Design

The M023 kill-switch design describes the emergency teardown information a
future first real launch review would need. It does not implement termination.

The design requires operator-visible active resources, a resource ledger path,
an owned instance ID list, max runtime deadline, budget threshold, termination
verification loop, audit log path, failure escalation steps, and no secret
printing.

Any executable terminate command is forbidden in M023. Automatic termination is
not implemented. The design is evidence for review only and keeps
`launch_ready=false` and `launch_allowed=false`.
