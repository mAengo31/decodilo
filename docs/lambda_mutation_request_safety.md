# Lambda Mutation Request Safety

M024 adds review-only request safety artifacts:
- request builder
- request redaction
- idempotency plan
- budget lock
- resource scope

The request builder validates evidence and can produce a redacted request plan.
It cannot produce an executable URL, executable HTTP method, or request body.

Request redaction removes API keys, authorization values, bearer tokens, SSH key
material, filesystem details, private IPs, and setup/user-data script content.
Setup scripts are rejected for M024 review plans.

Budget locks and idempotency plans are evidence artifacts only. Resource scope
accepts planned placeholders for review and rejects unowned live resources.
None of these artifacts enable launch.

## Milestone 027

M027 reuses these artifacts to prepare minimal launch and terminate request
models for fake-server-only execution. The prepared request may carry future
endpoint template metadata, but real Lambda URLs are rejected and real Lambda
request permission remains false.

Launch preparation requires budget, approval, ledger, teardown, and idempotency
hashes. Terminate preparation requires owned-resource scope, ledger, termination
verification, and idempotency hashes. Missing evidence blocks fake execution,
and complete evidence still does not enable real execution.
