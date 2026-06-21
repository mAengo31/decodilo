# Lambda Fake Mutation API

M022 adds a fake mutation-shaped Lambda API harness. It models future launch,
terminate, restart, SSH-key, and filesystem request/response shapes without
touching real Lambda.

The harness is fake-only:
- no real Lambda base URL is accepted
- no API key is accepted
- no network is used by default
- all generated resource IDs use `fake-i-*`, `fake-key-*`, or `fake-fs-*`
- every response keeps `fake_only=true`
- every response keeps `real_lambda_api_used=false`
- every response keeps `billable_action_performed=false`

The fake API is intentionally separate from the live read-only transport. Live
Lambda remains GET/read-only, while mutation-shaped behavior is modeled only in
local fake state.
