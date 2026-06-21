# Artifact Backend Interface

Milestone 010 introduces an artifact backend interface without adding remote
storage. The goal is to make future S3/GCS/object-store work explicit while
keeping this build local-only.

## Local Backend

`LocalFilesystemArtifactBackend` wraps the existing content-addressed local
chunk store. It can write, read, list, and verify local artifact bytes.

Backend references are JSON-serializable and include backend type, URI/path,
artifact id, and optional metadata.

Milestone 011 adds backend-neutral range and chunk operations:
`iter_chunks`, `read_range`, `validate_manifest`, `validate_chunks`, and
`artifact_size`.

## Disabled Remote Backend

`DisabledRemoteArtifactBackend` is a deliberate stub. Read, write, and list
operations raise `RemoteBackendDisabledError`.

There is no S3, GCS, Azure, Lambda, or remote object-store client. The disabled
backend reads no credentials, performs no network calls, and cannot be used to
launch or fetch cloud resources accidentally.

## Future Remote Backend Requirements

A real remote backend must prove authentication, encryption, content integrity,
retry/idempotency behavior, bandwidth and cost accounting, cleanup/retention,
preflight integration, and replay/checkpoint compatibility before it is enabled.

Until those requirements are implemented, preflight reports
`remote_backend_enabled=false`.

## Milestone 015 Contract And Simulator

Milestone 015 adds a formal remote backend contract and a local simulator. The
contract lists future operations such as conditional manifest put, range reads,
delete transactions, lifecycle marks, and health checks. The simulator can model
latency, bandwidth caps, throttling, consistency delays, retries, corruption,
and lifecycle delete behavior without making network calls.

The simulator is evidence for design review only. It is not a remote backend and
does not change `remote_backend_enabled=false`.

## Milestone 016 Readiness Evidence

Milestone 016 formalizes future backend review with a readiness gate,
conformance suite, evidence package, symbolic credential/auth models, and a
manual provider matrix. These remain local-only planning artifacts.
