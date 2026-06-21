# Lambda Resource Ledger

The Lambda resource ledger compares dry-run planned resources with fake
discovered resources. It records planned nodes, discovered fixture instances,
ownership tags, cost-attribution metadata, and orphan candidates.

In M018 the ledger is evidence only:
- no live resources exist
- no launch is recorded
- no termination is recorded
- unmanaged fake instances are flagged for review

The ledger is a safety primitive for future billing and teardown validation. A
future launcher must prove that every live resource is recorded before launch
and reconciled during teardown.

M019 live ledgers reconcile live read-only discovery reports against dry-run
plans. They may flag unmanaged resources for manual review, but they do not
emit executable terminate commands and cannot mutate Lambda resources.

M019A live ledgers classify discovered instances as running, pending, stopped,
terminated, or unknown. Running and pending unmanaged resources increment
`billable_state_count` and set `manual_review_required=true`. The report remains
advisory only and still performs no launch, termination, restart, create, or
delete operation.

M021 fake lifecycle reconciliation adds synthetic fake resources to local state
only. It compares planned fake resources, fake-created resources, fake-terminated
resources, fake orphans, and unmanaged live counts from read-only evidence. It
does not generate executable terminate commands.
