# Lifecycle Smoke Shape Selection

Lifecycle smoke tests should use the cheapest suitable candidate that can
exercise launch, read-only verification, owned termination, and read-only
termination verification.

Ranking order:

1. Prefer live-available candidates.
2. Prefer lower buffered 30 minute cost.
3. Prefer single-GPU shapes for smoke tests.
4. Require no filesystem dependency.
5. Require Strand-compatible launch payloads.
6. Require an existing SSH key name from read-only discovery.

Catalog-only selections are planning evidence, not live capacity proof. They
must be marked as risk-accepted in a future supervised launch milestone.
