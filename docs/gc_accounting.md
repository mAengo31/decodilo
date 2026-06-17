# GC Accounting

Milestone 013 splits artifact GC accounting into disjoint partitions and policy
overlays so operators do not have to infer the meaning of counts.

Reachability is a disjoint partition:

```text
reachable_count + unreachable_count + unresolved_count
  == unique_artifacts_scanned
```

Protection is an overlay. A protected artifact is usually also reachable, so
`protected_count` is not added to reachability totals. Retention labels are
also policy labels: a file may be reachable and retained, or unreachable and
temporary. Reports include `overlaps_explained` for these cases.

Each artifact classification records:

- artifact kind, such as manifest, chunk, checkpoint, event segment, snapshot,
  report, run spec, recovery manifest, global state, spill, temp, or unknown
- reachability state: reachable, unreachable, unresolved
- protection state: protected or unprotected
- retention state: retained, gc_eligible, temporary, orphaned, or deleted
- reference reasons and byte size

Destructive GC remains opt-in. `artifacts gc-plan` is dry-run only, and
`artifacts gc --apply` uses a transaction log and trash staging before moving
delete candidates.

