# Lambda Owned Instance Reconciliation

Owned-instance reconciliation determines whether an instance can be safely
treated as created by the M029 launch attempt.

Confidence levels:

- `exact`: the launch response or journal recorded an owned instance ID.
- `high`: a single read-only candidate matches the planned shape and region.
- `medium` / `low`: insufficient for automatic termination.
- `none`: no candidate is visible.

Termination is allowed only for exact or high-confidence owned matches. Unowned
or ambiguous candidates must not be terminated by automation.

For a future second attempt, M030 keeps this rule and adds an explicit
reconciliation plan: low or no confidence candidates are non-terminable, and
read-only termination verification remains mandatory after any owned terminate.

M031D applies the same ownership rule to the second response-loss incident. If
no owned instance ID is recorded and read-only discovery has no candidates,
automation has no termination target. Future launches remain held for repeated
response-loss mitigation even when the incident closes.
