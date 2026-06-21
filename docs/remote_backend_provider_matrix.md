# Remote Backend Provider Matrix

The provider matrix compares future backend candidates using manual capability
input only. There is no live validation, SDK, credential, or network access.

The matrix scores throughput, latency, consistency, integrity, security,
lifecycle, cost, and operational complexity.

Provider entries must declare `data_source="manual"` and
`is_live_validated=false`. Missing conditional put, insufficient bandwidth,
missing authentication, or missing delete transaction logs produce blockers.

The matrix is planning evidence only and does not enable remote backend
execution or cloud launch.

Milestone 017 uses the manual provider matrix to populate provider assessments
and implementation proposals. Provider candidates remain manual-only and
`is_live_validated=false`.
