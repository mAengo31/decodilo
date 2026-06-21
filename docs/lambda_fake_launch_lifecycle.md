# Lambda Fake Launch Lifecycle

M021 rehearses the Lambda launch lifecycle using local fake state only. It does
not call Lambda, does not use credentials, and does not create cloud resources.

The fake launch executor consumes M020 evidence, a fake lifecycle approval
manifest, and a dry-run launch plan. It refuses to run unless:
- `fake_mode=true`
- the dry-run launch plan remains non-launchable
- M020 price and resource reconciliation passed
- the first-launch policy passed
- approval status is `approved_for_future_fake_launch_lifecycle`
- no unmanaged billable resources are present

Fake resources use synthetic IDs such as `fake-i-*`. Real Lambda IDs from live
read-only discovery cannot be used as fake-created resource IDs.

Every report keeps:
- `fake_only=true`
- `real_lambda_api_used=false`
- `billable_action_performed=false`
- `launch_ready=false`
- `launch_allowed=false`

This rehearsal proves journal, idempotency, failure recovery, and teardown
accounting before any real mutation-capable design work.

M022 routes fake launch through the fake mutation-shaped API harness before
journaling lifecycle transitions. The fake API response is stored as journal
metadata so future reviewers can inspect mutation-shaped request/response
coverage without enabling real Lambda mutation.
