# Lambda First Launch Policy

M020 defines policy limits for a future first Lambda launch, but it does not
implement launch execution.

Default future first-launch limits:
- max instances: `1`
- max runtime: `30` minutes
- max run budget: `$50`
- teardown plan required
- termination verification plan required
- resource ledger required
- budget manifest required
- price reconciliation required
- live read-only discovery required
- read-only audit required
- human approval required
- no unmanaged billable resources allowed
- current build must keep cloud launch disabled

Policy violations are reported as planning blockers. The policy report itself
always keeps `launch_ready=false` and `launch_allowed=false`.

M021 uses the policy as an input to fake lifecycle rehearsal. Passing the policy
can qualify only a local fake launch lifecycle candidate. It still does not
enable real Lambda launch, teardown, restart, create, delete, SSH, setup, or
training behavior.

M023 consumes the policy in a first-launch safety case. The safety case can
document that one instance, 30 minutes, and $50 are the review limits, but it
still cannot approve real launch or mutation.
