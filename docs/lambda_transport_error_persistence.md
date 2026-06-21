# Lambda Transport Error Persistence

Transport error persistence converts `LambdaRealMutationTransportError` and
related timeout/parser failures into local JSON evidence.

The normal artifact is `transport-error.json`; the combined artifact is
`mutation-failure-report.json`. If the normal write path fails, the runtime
writes `mutation-failure-fallback.json` with minimal non-secret evidence.

This path is designed for failures after a request may have been sent. It keeps
manual review required and preserves the no-retry rule.
