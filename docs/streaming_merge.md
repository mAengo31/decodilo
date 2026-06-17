# Streaming Merge

The production merge rule is still the SGD-style token-weighted outer update:

```text
W_new = W_global + outer_lr * weighted_delta
```

where each learner delta is weighted by accepted token count.

## In-Memory Mode

`merge_mode=in_memory` materializes learner vectors and uses the original
token-weighted merge. This remains the default for tiny local runs.

## Streaming Chunked Mode

`merge_mode=streaming_chunked` processes accepted numeric fragments through the
streaming merge helper. For small arrays, tests assert the output matches the
in-memory merge within tolerance. Metrics record bytes read, bytes written,
chunks processed, and a peak working-byte estimate.

## Binary Streaming Merge

Milestone 010 adds a binary merge path for `tensor_binary_v1` fragment
artifacts. The merge validates artifact refs, manifest hashes, chunk hashes,
dtype, shape, and finite numeric values before using fragment data. For small
numeric arrays, tests assert binary streaming merge matches the in-memory merge
for one learner, multiple learners, unequal token weights, zero-token
exclusion, and different outer learning rates.

The helper reports:

- `binary_streaming_merges`
- `binary_streaming_merge_bytes_read`
- `binary_streaming_merge_bytes_written`
- `binary_streaming_merge_chunks_read`
- `binary_streaming_merge_chunks_written`
- `binary_streaming_merge_peak_working_bytes_estimate`
- `binary_streaming_merge_wall_time_seconds`

Milestone 011 routes the binary path through `MergePlan` and
`out_of_core_token_weighted_merge`. The helper processes element blocks under a
configured `max_working_bytes`, rejects unsupported dtype/shape/layout cases,
and reports block counts and peak working-byte estimates.

## Replay Modes

Chunked numeric replay runs in `numeric_recompute` mode when referenced
artifacts are available. Missing or corrupt artifacts fail replay. Metadata-only
large-state simulation must be explicitly labeled as simulation-only and cannot
be presented as real numeric training progress.
