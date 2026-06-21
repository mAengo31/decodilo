# Lambda Support Evidence Request

M035 can generate a support/operator evidence request before any further real
launch attempt. The request asks for:

- correct launch endpoint path and method,
- expected launch response shape,
- behavior for empty, non-JSON, lost, or timeout responses,
- idempotency behavior,
- launched instance identity fields,
- account-specific availability endpoints,
- quota and usage endpoint support,
- termination terminal states,
- launch and terminate rate limits.

The request contains no secrets and performs no Lambda API calls.

M036 adds a stricter support confirmation request and ingestion model. After
three ambiguous launch outcomes, endpoint confidence cannot upgrade to high
unless ambiguous launch behavior and termination verification semantics are
answered.
