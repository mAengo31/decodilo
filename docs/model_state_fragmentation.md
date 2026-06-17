# Model State Fragmentation

Real trainers usually expose a state-dict-like mapping from tensor names to
tensors. Milestone 006 adds a generic named tensor state layer while preserving
the current syncer merge contract.

## Named Tensor State

`NamedTensorState` represents CPU-portable model state:

- tensor name
- dtype
- shape
- optional device label
- tensor checksum
- global version
- state schema version

Numpy arrays are supported by default. Future torch tensors must be converted to
CPU arrays at the adapter boundary before serialization.

## Tensor Manifest

`TensorManifest` deterministically sorts tensor names and records each tensor's
offset and length in the flattened view. The manifest checksum covers tensor
metadata and tensor checksums.

## Flattening

The trainer adapter owns conversion from named tensors to a flat numeric vector.
The syncer still sees flat fragments because quorum, staleness, replay, and
token-weighted merge are trainer-agnostic.

Flattening invariants:

- tensor names are sorted deterministically
- dtype and shape are preserved in the manifest
- offsets cover the full flat vector without gaps or overlap
- identical states produce identical checksums
- corrupted tensor or flat-fragment checksums are rejected

## Fragmentation

`FragmentLayout` splits the flat vector by element count. If more fragments are
requested than elements, empty fragments are not emitted. Fragment checksums
cover offset, length, data, global version, and manifest checksum.

## Reconstruction

Reconstruction validates fragment coverage, fragment checksums, manifest
checksum, and tensor checksums before returning named tensors.

## Limits

This is still an in-memory CPU scaffold. Very large production models will need
streaming, chunked IO, compression-aware layouts, and possibly sharded manifests.
Those additions must preserve the same manifest, checksum, and replay
invariants.

Milestone 007 uses the same named-state path for the optional tiny causal-LM
trainer. Torch tensors are converted to CPU numpy arrays before serialization,
strict tensor names and shapes are checked on load, and corrupted or nonfinite
tensors are rejected.

## Milestone 008 Large-State Readiness

Milestone 008 adds synthetic large-state sources and chunked named-state
helpers so tests can reason about logical model sizes much larger than memory
without allocating the whole state. Chunks are generated deterministically from
run id, learner id, tensor name, chunk index, and seed.

The syncer still performs real numeric updates on flat fragments for small
runs. For large metadata-only tests, the system validates layout, byte counts,
and hash lineage without pretending to perform a real numeric merge.
