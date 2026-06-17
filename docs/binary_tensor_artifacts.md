# Binary Tensor Artifacts

Milestone 010 adds `tensor_binary_v1`, a production-shaped local tensor artifact
codec. It replaces toy JSON numeric payloads on the chunked path with raw
tensor bytes plus deterministic JSON metadata.

## Format

A tensor artifact has two layers:

- Content-addressed chunk files containing raw tensor bytes.
- A deterministic `StorageArtifactManifest` whose metadata contains
  `codec="tensor_binary_v1"` and a `tensor_binary` metadata block.

The tensor metadata records each tensor's name, dtype, shape, element count,
byte order, byte offset, byte length, chunk range, and SHA-256 checksum. Tensor
names are sorted deterministically before encoding.

## Supported Dtypes

The allowlist is intentionally narrow:

- `float16`
- `float32`
- `float64`
- `int8`, `int16`, `int32`, `int64`
- `uint8`
- `bool`

`bfloat16` currently fails clearly because numpy does not provide a portable
stdlib representation here. Object, ragged, complex, and unsupported dtypes are
rejected.

## Byte Order

Numeric tensors are canonicalized to little endian before writing. Boolean and
byte-like values use `not_applicable`. Big-endian numeric inputs are accepted
only by converting into the canonical little-endian representation.

## Safety

The codec does not use pickle, `torch.save`, dynamic imports, or arbitrary code
execution. It validates:

- manifest hash and root hash
- every chunk hash
- tensor byte ranges and total bytes
- tensor checksums
- duplicate tensor names
- unsupported dtypes
- absurd shapes or integer overflow risk
- non-finite numeric tensors when finite policy is enabled

Corruption or mismatch fails closed with an invariant/storage error.

## Range Reads

Milestone 011 adds range-oriented artifact reads for binary artifacts. The
range reader validates manifests and chunk hashes before returning bytes and
rejects negative, overflowing, or out-of-bounds ranges. Out-of-core merge uses
these range reads to load only the active tensor block from each learner
artifact.

## Limitations

Compression is `none` by default. Optional compression is not part of the live
runtime path yet. Torch tensors may be converted by optional torch helpers, but
the storage package itself does not import torch.
