# Lambda Safety Preflight

Lambda preflight validates the offline evidence required before any future
read-only Lambda work:
- fake discovery report
- symbolic credential policy
- mutation guard denial of mutations
- resource ledger
- dry-run launch plan
- dry-run teardown plan
- budget and price snapshot references when provided

Preflight always keeps:
- `launch_enabled=false`
- `launch_ready=false`
- `launch_allowed=false`

Missing evidence is reported as warnings or errors depending on safety impact.
Raw credentials, enabled launch plans, enabled teardown plans, live API usage,
or live resource IDs fail preflight.

M019 live preflight accepts live API usage only when it appears in a
read-only discovery report with a passing read-only audit. Even then,
`launch_ready=false` and `launch_allowed=false` remain enforced.

M019A live preflight also validates endpoint calibration, redaction status,
the read-only audit status, and live ledger manual-review signals. If unmanaged
running resources are discovered, preflight may pass as
`passed_read_only_with_warnings`, but it sets `manual_review_required=true` and
still remains non-launchable.

M020 preflight may also include a combined readiness report. When present,
preflight summarizes price reconciliation, resource reconciliation, first-launch
policy, approval gate, blocker count, and fake-lifecycle candidacy. Missing
M020 evidence is a warning. A candidate fake lifecycle still does not enable
launch; `launch_ready=false` and `launch_allowed=false` remain enforced.

M021 fake lifecycle preflight checks the M020 report, fake-only approval
manifest, first-launch policy, price reconciliation, resource reconciliation,
budget/runtime/instance limits, teardown evidence, read-only discovery evidence,
and disabled real launch state. Passing fake lifecycle preflight means only that
the local rehearsal may run; real Lambda launch remains impossible.

M023 preflight may summarize the real mutation boundary proposal, first-launch
safety case, evidence package, and review record. If a review record reaches
`design_review_ready`, preflight still reports "design review ready only; real
mutation remains disabled" and keeps `launch_ready=false` and
`launch_allowed=false`.

M025 preflight may summarize final prelaunch review, semantic mutation audit,
spend safety, secret handling, resource ownership, and go/no-go status. If the
go/no-go record reaches `go_for_future_m026_real_launch_review`, preflight
still reports that launch remains disabled in this build.

M026 preflight may summarize the decision record, M027 authorization record,
blocker matrix, and evidence freshness report. If the M026 decision approves
M027 minimal implementation, preflight reports "M027 implementation
authorization only; launch remains disabled" and still keeps
`real_mutation_enabled=false`, `launch_ready=false`, and
`launch_allowed=false`.
