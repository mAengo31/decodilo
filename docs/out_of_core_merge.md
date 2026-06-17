# Out-Of-Core Merge

Milestone 011 adds a plan-based binary merge path for local tensor artifacts.
The goal is to prove memory-bounded merge behavior before any GPU, cloud, or
remote artifact backend exists.

## MergePlan

`MergePlan` records:

- run id, round id, and fragment id
- input artifact refs
- optional global/output artifact refs
- token weights
- outer learning rate
- dtype, shape, and total element count
- chunk size
- maximum working bytes
- finite-value policy
- whether the merge is numeric or metadata-only simulation

Plans serialize deterministically for audit and replay diagnostics.

## Block Processing

`out_of_core_token_weighted_merge` reads only the current element block from
each accepted learner artifact. It validates tensor manifests and chunk hashes
before reading ranges, excludes zero-token learners, and estimates peak working
bytes as the active block buffers rather than all learner artifacts.

If `max_working_bytes` cannot hold even one element from the required buffers,
merge fails closed.

## Dtype Policy

The numeric path supports `float32` and `float64`. `float16` is accepted by the
plan model and may be promoted internally when needed. Non-floating and object
dtypes are rejected for numeric merge.

## Numeric vs Metadata-Only

Metadata-only plans are explicit:

- `numeric_merge_performed=false`
- `simulation_only=true`

They are useful for large logical state and event-log tests, but they are not
real ML progress.

## Limitations

The current live local runtime still keeps small global vectors in memory for
the toy trainer. The important M011 guarantee is that binary learner artifact
access and merge validation use range-oriented reads and bounded block metrics.

## Lifecycle Interaction

Out-of-core merge artifacts are covered by artifact reachability and GC plans.
Latest global-state artifacts and checkpoint/snapshot-referenced merge outputs
must remain protected. Metadata-only synthetic large-state plans remain
simulation-only and should not be treated as numeric training progress during
preflight or replay.
