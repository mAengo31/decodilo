# Lambda Real Mutation Execution Guard

The M024 execution guard evaluates the evidence a future mutation request would
need: operation spec, approval, budget lock, resource scope, teardown plan,
termination verification policy, idempotency key, kill-switch design, live
read-only discovery, clean ledger, and launch-window policy.

The guard can report that review-only prerequisites are present, but
`execution_guard_passed_for_execution=false` is enforced. The
`current_milestone_forbids_execution` criterion remains a blocker for execution.

No config, CLI flag, approval artifact, or environment variable can make this
guard executable in M024.

## Milestone 027

M027 adds a separate minimal mutation execution policy for fake-server-only
execution. It can allow local fake launch/terminate rehearsal when all evidence
is present and the base URL is localhost or an in-memory fake transport.

The real execution guard remains non-executable. Real Lambda URLs,
credentials, unknown endpoints, and non-fake modes are blockers. Real execution
permission remains false even when fake execution passes.
