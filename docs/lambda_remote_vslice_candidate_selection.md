# Lambda Remote Vertical-Slice Candidate Selection

The M067S selector changes the future Decodilo vertical-slice rule from cheapest-live-first to SSH-readiness-first.

Selection order:
1. Require fresh read-only discovery for any future live attempt.
2. Prefer an SSH-proven candidate/region pair.
3. Exclude candidate/region pairs with recent `ssh_port_not_reachable`.
4. Use cost only after SSH readiness is considered.
5. If no SSH-proven candidate is live, stop and require operator approval before exploring a new candidate/region.

M067S does not authorize immediate launch. It records:

```text
retry_decision_status=wait_for_ssh_proven_candidate_live
authorization_status=not_authorized
```

Standing flags remain `launch_ready=false` and `launch_allowed=false`.
