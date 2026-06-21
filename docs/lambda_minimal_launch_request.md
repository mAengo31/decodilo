# Lambda Minimal Launch Request

The M027 launch request model is a fake-server-only representation of a future
single-instance Lambda launch request.

Required fields include:
- instance type
- region
- idempotency key
- dry-run plan hash
- budget lock hash
- approval manifest hash
- resource ledger hash
- teardown plan hash

Optional review fields include image and existing SSH key or filesystem
references. M027 does not create keys, filesystems, setup scripts, SSH sessions,
or training workloads.

Prepared launch requests may include endpoint template metadata for review, but
they do not permit real Lambda execution. Real Lambda request permission remains
false, and real Lambda URLs are rejected by the execution context.

