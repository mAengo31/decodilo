# Lambda Response Loss Mitigation

M030 requires a stricter response-loss mitigation review before any future
second launch attempt can be considered.

Required mitigations:

- pre-launch read-only discovery immediately before a future request
- deterministic idempotency key distinct from the M029C key
- journal event and request hash before send
- planned shape, region, and image recorded before send
- no automatic launch retry after timeout or lost response
- immediate post-timeout read-only discovery
- candidate matching by shape, region, and time window where available
- exact or high-confidence ownership before termination
- manual console review if uncertainty remains

Missing mitigation blocks M030 second-attempt authorization.
