# Lambda Real Launch Blocker Matrix

The M026 blocker matrix separates blockers for M027 implementation
authorization from blockers for actual real launch execution.

M027 implementation blockers include:
- missing or incomplete human review
- stale or missing freshness evidence
- failed semantic mutation audit
- failed secret or ownership evidence when supplied by the review flow

Real launch blockers remain present in M026 even when M027 authorization is
approved:
- M026 cannot enable launch
- launch is disabled by policy
- launch execution is not implemented

This distinction allows a future implementation milestone to be authorized
without claiming launch readiness.
