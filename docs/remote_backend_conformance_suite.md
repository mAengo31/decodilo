# Remote Backend Conformance Suite

The provider-neutral conformance suite runs against the local simulator and the
disabled backend. It does not use a network, SDK, credential, or cloud API.

Cases cover artifact put/get/range/list/delete, integrity failures, stale or
non-monotonic visibility, conditional put conflicts, retry/idempotency, partial
write safety, lifecycle/delete transaction behavior, replay/checkpoint restore,
symbolic auth scopes, and bandwidth/cost accounting.

The suite includes a passing simulator profile and failing profiles for missing
conditional put, weak consistency, undetected corrupt reads, missing delete
transaction behavior, missing auth scopes, and insufficient bandwidth.

The disabled remote backend must remain disabled and cannot pass as usable.
