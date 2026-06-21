# Lambda Launch Response Loss Hardening

Future launch attempts must treat a lost launch response as a potentially
billable ambiguous state.

Hardening requirements:

- Record request hash, idempotency key hash, planned shape, planned region, and
  send timestamp before sending the launch request.
- Take pre-launch and post-timeout read-only discovery snapshots.
- Match possible owned candidates by shape, region, status, visibility, and
  launch time window where available.
- Do not automatically retry launch after response loss.
- Do not terminate unless ownership is exact or high confidence.
- Require manual review if candidate matching is ambiguous.

Provider-visible metadata/tag correlation is recorded as a limitation until the
Lambda API is proven to support it for launch requests.

M030 adds a response-loss mitigation review for any future second attempt. The
review requires a new idempotency key, no automatic retry, request hash capture,
pre/post read-only discovery, and manual console review for ambiguity.

M031D escalates this policy after a second response-loss event. A repeated
response-loss review is now required before any future launch. The review must
distinguish transport timeout, malformed response, HTTP error, and endpoint
mapping uncertainty, and it must capture redacted HTTP status/header/body-size
metadata before any future response parsing.
