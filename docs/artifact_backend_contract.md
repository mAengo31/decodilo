# Artifact Backend Contract

Milestone 011 extends the artifact backend boundary with range and chunk access.
This is still local-only.

## Required Operations

Backends expose:

- `iter_chunks`
- `read_range`
- `validate_manifest`
- `validate_chunks`
- `artifact_size`

Range reads validate chunk hashes before returning bytes and reject negative,
overflowing, or out-of-bounds ranges.

## Local Backend

`LocalFilesystemArtifactBackend` supports the full contract against the local
content-addressed chunk store. It can also read simple content-addressed byte
refs from earlier milestones.

## Disabled Remote Backend

`DisabledRemoteArtifactBackend` raises for every operation. It cannot be made
usable by configuration strings, wrappers, or preflight. Cloud preflight reports
`remote_backend_enabled=false`.

## Fault-Injected Backend

The fault-injected wrapper simulates local transient failures, corruption, slow
operations, duplicate writes, and partial write failures. It is deterministic
from a seed and is for tests only.

## Future Remote Requirements

A future remote backend must prove authentication, integrity, retries,
idempotency, bandwidth accounting, cleanup/retention, preflight integration,
and replay/checkpoint compatibility before it can be enabled.
