# Lambda Fake Server Execution Only

M027 fake execution uses local fake transports and fake server state only. It
does not use Lambda credentials and does not send requests to Lambda Cloud.

Allowed targets:
- in-memory fake transport
- localhost / `127.0.0.1` fake server when explicitly configured

Rejected targets:
- Lambda Cloud API URLs
- non-localhost URLs
- contexts containing credential references
- contexts with real execution flags enabled

The fake server models launch and termination responses with synthetic resource
IDs. Duplicate launch and terminate requests use idempotency keys so retries
return the same fake resource state rather than creating duplicates.

Failure modes such as response loss, timeout-after-create, timeout-after-
terminate, and malformed responses are deterministic and local.

