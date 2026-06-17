# Artifact Transport

Milestone 009 uses local shared-filesystem artifact references to move chunked
payloads between learner and syncer processes.

## ArtifactRef

An `ArtifactRef` contains:

- artifact id and type
- manifest path
- chunk root
- total bytes
- manifest hash and content root hash
- run id and creator id
- storage backend, currently always `local_filesystem`
- metadata such as dtype, shape, global version, and checksums

Refs are JSON-serializable and use stable sorted-key serialization.

## Path Safety

The local transport rejects:

- path traversal
- absolute paths unless explicitly allowed and inside configured roots
- manifest paths outside the workdir/artifact root
- chunk roots outside the workdir/artifact root
- symlink escapes where the platform exposes them through `Path.resolve`
- `file://` and other URL-like paths
- missing manifests, missing chunk roots, directories in place of manifests, and
  corrupt hashes

No remote URLs, S3/GCS paths, network fetches, shell commands, or cloud APIs are
allowed.

## Backend Scope

This is intentionally not the final production artifact transport. It proves
the runtime protocol, idempotency, replay, and path-safety semantics with local
files before a later remote artifact backend is designed.
