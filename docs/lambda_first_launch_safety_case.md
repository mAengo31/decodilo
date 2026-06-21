# Lambda First Launch Safety Case

The M023 safety case records the claims that must hold before a later milestone
can review a first real Lambda launch implementation. It is not approval to
launch.

Required claims include one instance only, a maximum $50 budget, a maximum
30-minute runtime, a teardown plan, a termination verification policy, human
approval, no unmanaged billable resources, fresh price evidence, an idempotency
key, an active bounded launch window, and passing fake lifecycle evidence.

The safety case also records exclusions for first launch: no training workload,
no SSH, and no setup script unless separately reviewed later.

If fake lifecycle evidence, operation spec, or termination verification policy
is missing, the safety case remains blocked. Regardless of status,
`launch_ready=false` and `launch_allowed=false`.

M024 budget locks, idempotency plans, and resource scopes can reference the
safety case as review evidence only. They do not approve a first launch and do
not change the disabled launch flags.

M025 adds runbooks, operator checklist, semantic no-mutation audit, spend
safety review, and go/no-go record around this safety case. A positive M025
record can only recommend future M026 real-launch review.
