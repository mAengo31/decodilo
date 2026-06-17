# Memory Budgeting

Milestone 008 adds explicit memory and spill budgeting primitives.

## Memory Limits

`MemoryBudget` tracks:

- max in-memory bytes per fragment
- max total in-memory bytes
- current and peak in-memory bytes
- current and peak spill bytes
- spill allowance and spill budget

Payloads over budget raise `MemoryBudgetExceeded`.

## Spill To Disk

`SpillManager` writes oversized payloads into the chunk store when spill is
allowed. Spill files are local-only and can be cleaned up after a run unless
retention is explicitly requested.

## Byte-Level Backpressure

Runtime submissions now include declared payload bytes. The syncer compares
declared and actual message size, records size mismatch as backpressure, and
separates:

- message count pressure
- byte pressure
- memory budget pressure
- spill budget pressure

Rejected payloads do not count as useful tokens and do not mutate global state.

## Report Counters

Local reports include non-replayable `perf_counters` such as wall time,
serialized bytes, transport byte counters, peak memory estimate, and spill byte
counters. Replay does not depend on these counters.

