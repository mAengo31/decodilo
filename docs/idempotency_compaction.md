# Idempotency Compaction

Milestone 012 adds a typed `IdempotencyStore` around fragment submission decisions. Each
record binds a run id, idempotency key, learner, fragment, token count, decision, payload
checksum or artifact hash, logical time, and global-version watermarks.

Duplicate submissions are never allowed to double-count useful tokens. Accepted duplicates
return a duplicate decision for the original accepted record; rejected duplicates remain
rejected with the original reason.

Compaction is watermark based:

- `global_version_watermark` and `logical_time_watermark` identify old records.
- in-flight records are protected.
- the newest recovery and duplicate-suppression windows are protected.
- compacted records become tombstones, not silent deletion.

If a duplicate arrives after its full record has expired, the store returns
`expired_duplicate`. The safe policy is to reject it rather than treating it as a fresh
fragment.

## Milestone 013 Stress Behavior

Synthetic stress tests generate thousands of accepted, rejected, and duplicate
records without a slow runtime run. Compaction by global version, logical time,
and max-record limits must be deterministic. Protected in-flight records and
records inside the recovery window survive. Expired records leave tombstones so
old duplicates are rejected as expired duplicates after compaction.
