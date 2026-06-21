# Lambda Fake Orphan Detection

Fake orphan detection finds local synthetic resources that remain in
non-terminal states after a fake lifecycle run. Examples include `running`,
`unhealthy`, `failed_launch`, and `failed_terminate`.

The reconciler also carries forward unmanaged live-resource counts from the
read-only ledger. Those live resources are advisory evidence only. The fake
lifecycle never generates real termination commands and never mutates Lambda.

Reports include:
- `fake_orphan_count`
- `unmanaged_live_count`
- `manual_review_required`
- `no_mutations_performed=true`
- `real_lambda_api_used=false`
- `billable_action_performed=false`
