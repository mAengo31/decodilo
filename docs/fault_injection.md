# Fault Injection

Milestone 011 adds deterministic local fault injection around artifact backend
operations. It does not use the network.

## Faults

The wrapper can simulate:

- transient read failures
- transient write failures
- permanent read failure
- corrupted reads
- slow read/write calls
- duplicate writes
- partial write failure before commit

## Retry Policy

`RetryPolicy` defines maximum attempts, retryable exception types, and optional
backoff. Tests use zero backoff. Retried operations must preserve idempotency;
duplicate writes to the local backend return the same content-addressed ref.

Corruption is detected by checksum validation. A corrupted read is not silently
converted into success unless a later clean read is explicitly configured.

## Metrics

Backend metrics include reads, writes, retries, failures, detected corruption,
bytes read, and bytes written.
