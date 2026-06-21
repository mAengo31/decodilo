# Lambda Second Launch Gate

M029D adds a second-attempt blocker.

If a prior M029 attempt sent a launch request and did not complete with clean
termination verification, a later M029 launch preflight must reject execution
until the incident report reaches one of:

- `closed_no_instance_visible`
- `closed_manual_termination_verified`

Clearing the incident blocker does not itself authorize launch. All normal
M029/M030 budget, operator, read-only, ownership, and termination gates still
apply.

M030 can clear only the incident-review blocker and can authorize only a future
M031 second-launch review. It still cannot emit launch-ready, launch-allowed, or
execute-now status.

M031D adds a stricter global hold after M029C and M031 both lost launch
responses. Even if the M031 incident closes as `closed_no_instance_visible`,
future launch remains blocked until repeated response-loss review and mitigation
are accepted.
