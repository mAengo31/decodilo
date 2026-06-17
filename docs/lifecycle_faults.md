# Lifecycle Faults

Milestone 013 adds lifecycle corruption and failure-safety checks around
artifacts, event segments, replay snapshots, recovery manifests, and GC
transactions.

The validation path is expected to catch:

- corrupted artifact chunks or hash mismatches
- missing chunks or manifests
- corrupted event segments
- corrupted replay snapshots
- corrupted or regressed recovery manifest chains
- failed or incomplete GC transactions
- missing latest global state or checkpoint references
- artifact manifest omissions for compact outputs
- unresolved required references

GC apply uses a transaction log under `.decodilo_gc_transactions/` and stages
delete candidates under `.decodilo_trash/<transaction_id>/`. If a delete fails
halfway, the transaction is marked failed and `run validate` reports it. A
future GC pass can re-plan from the current filesystem state.

