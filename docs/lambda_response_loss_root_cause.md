# Lambda Response-Loss Root Cause

M032 treats the repeated M029C and M031 launch response losses as a transport
diagnostics failure, not as permission to retry launch.

The suspected category remains `client_timeout_too_short` until diagnostics
prove otherwise. M032 records status, redacted headers, content type, content
length, body size, parse phase, and exception class before any future launch
response is parsed.

M032 does not launch, terminate, or mutate Lambda resources. It only produces
offline evidence for a future review.

M033 treats the suspected root cause as mitigated only for review purposes when
M032 mitigation acceptance, endpoint-spec operator confirmation, response-capture
settings, and timeout policy are all present. It does not perform another launch.

M036 keeps that mitigation in review-only mode and requires support/operator
confirmation before any future launch review can treat endpoint behavior as
high-confidence.

M036R supersedes the missing support-response path with a compatibility audit
against the operator-tested Strand-AI `lambda-cli`. The CLI is unofficial, so it
does not prove provider support behavior, but it does explain the likely
response-loss root cause: local launch/terminate shape handling must match
`POST /instance-operations/launch`, `data.instance_ids`, 30 second timeout, and
2xx status-only termination success before any future launch review.
