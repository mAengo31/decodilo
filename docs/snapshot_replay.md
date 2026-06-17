# Snapshot Replay

Event logs can now be segmented into a hash-chained set of JSONL files. The original
single `events.jsonl` format remains valid, but segmented mode lets long runs rotate logs by
event count, byte count, or checkpoint boundary.

Each segment records:

- first and last event id
- first and last logical time
- event count and byte size
- SHA-256 hash
- previous segment hash

Replay snapshots capture enough trusted state to avoid walking the whole run from event
zero: global version, logical time, last event id, global-state checksum or vector for local
CPU tests, useful-token totals, committed-round count, artifact refs, and idempotency
watermarks.

Replay can start from genesis or from a validated snapshot plus later segments. Snapshot
replay fails closed on hash mismatch, run-id mismatch, missing tail segments, or global
version regression after the snapshot.

## Milestone 013 Stress Checks

Long segmented replay tests create many event segments, validate the hash
chain, and compare replay from genesis with replay from the latest snapshot
plus tail segments. Deleting a segment before a valid snapshot may be acceptable
only when replay explicitly starts after that segment. Deleting or corrupting a
post-snapshot segment fails replay.

`python -m decodilo.cli replay compare --workdir /tmp/decodilo-run --genesis --snapshot latest`
prints both final global versions and useful-token counts.
