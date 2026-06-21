# Lambda Real Mutation Arming Gate

The M023 arming gate is a design object only. It lists future criteria that
would have to be complete before any mutation-capable code could be considered.

Criteria include explicit operator approval, max budget, max runtime, exactly
one instance, explicit shape and region, fresh read-only discovery, fresh price
reconciliation, a clean resource ledger, teardown and termination verification
plans, fake lifecycle stress, fake teardown audit, real mutation absence audit,
hash-locked plans and approvals, idempotency key, kill-switch plan, operator
presence, no background work, safe retry policy, and bounded launch window.

Even when every criterion is marked complete, M023 reports
`arming_gate_status=design_only`, `armed=false`, `real_mutation_enabled=false`,
and `launch_allowed=false`.

M024 adds an arming-state model for the disabled skeleton. It is stricter than
the design gate: any attempt to set `armed=true`,
`mutation_arming_allowed=true`, or execution-enabled flags fails validation.
