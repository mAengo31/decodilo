# Live Chunked Runtime

Milestone 009 moves chunked artifacts onto the live local runtime path.
Milestone 010 adds `tensor_binary_v1`, so chunked mode can carry production-
shaped binary tensor artifacts instead of only safe JSON numeric payloads.
Inline JSON payloads still work for tiny tests.

## Runtime Modes

`RunSpec` and `local run` support:

- `payload_storage_mode`: `inline`, `chunked`, or `auto`.
- `global_update_storage_mode`: `inline`, `chunked`, or `auto`.
- `checkpoint_storage_mode`: `inline`, `chunked`, or `dual`.
- `merge_mode`: `in_memory`, `streaming_chunked`, or `auto`.
- `artifact_root`, `chunk_store_root`, `inline_payload_max_bytes`, and
  `chunk_size_bytes`.
- `tensor_artifact_codec`, `fragment_artifact_codec`, and
  `checkpoint_artifact_codec`: `json_safe`, `binary_v1`, or `auto`.

`auto` stores payloads as artifacts once they exceed
`inline_payload_max_bytes`. `streaming_chunked` requires chunked or auto payload
storage.

## Learner Submissions

In chunked mode the learner serializes a `TrainerFragment` into a
content-addressed artifact and submits only an `ArtifactRef` plus metadata.
In `binary_v1` mode the artifact stores raw tensor bytes and a deterministic
JSON manifest with dtype, shape, byte ranges, and checksums. The event log
records artifact ids, manifest hashes, payload bytes, codec, dtype/shape
metadata, fragment id, global version, and token count. It never embeds binary
chunk bytes.

## Syncer Validation And Merge

The syncer validates artifact refs before accepting fragments:

- manifest path and chunk root must stay inside the configured workdir/artifact
  roots
- manifest hash, root hash, total bytes, run id, and chunk hashes must match
- malformed or corrupt artifacts are rejected before mutating global state
- duplicate idempotency keys reuse the original decision

When `merge_mode=streaming_chunked`, the syncer uses the streaming merge path
for accepted numeric fragments and writes merged global state as an artifact
when `global_update_storage_mode=chunked`.

With `fragment_artifact_codec=binary_v1`, the merge path validates
`tensor_binary_v1` artifacts before reading tensor bytes. Small numeric binary
runs are tested against the in-memory merge result.

## Global Updates

Chunked global updates are delivered as `global_vector_artifact_ref`. Learners
validate and read the artifact, apply it through `TrainerAdapter`, then send
`global_update_ack`. Acknowledgement is after successful local application.

With `tensor_artifact_codec=binary_v1`, global updates are delivered as binary
tensor artifacts and learners decode them through the same safe tensor artifact
reader before applying the update.

## Limitations

The artifact transport is a local shared filesystem only. There is no remote
artifact backend, no object-store client, no cloud launch, and no GPU
requirement in this milestone.
