# Lambda Price And Resource Reconciliation

Milestone 020 reconciles read-only Lambda discovery evidence with local price
snapshots and dry-run plans. It does not call a live pricing API and does not
call Lambda.

Shape matching compares:
- discovered instance types from fake or live read-only discovery
- the planned dry-run launch shape
- local price snapshot records

Match statuses are:
- `matched`
- `discovered_but_no_price`
- `priced_but_not_discovered`
- `ambiguous`
- `missing`

Price reconciliation fails closed for missing or ambiguous prices. Sample or
stale price snapshots are blockers for future real launch readiness unless the
operator explicitly marks them allowed for planning-only use. M020 reports may
still be generated with warnings, but `launch_ready=false` and
`launch_allowed=false` remain enforced.

Resource reconciliation compares the live/fake discovery report, live ledger,
dry-run launch plan, and dry-run teardown plan. Missing planned regions, images,
SSH keys, or filesystems are blockers. Unmanaged running resources require
manual review. Reconciliation never suggests executable terminate commands.
