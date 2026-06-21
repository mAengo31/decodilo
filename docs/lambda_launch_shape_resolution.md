# Launch Shape Resolution

M029B resolves a first-launch shape by matching:

- the planned launch shape
- product catalog evidence
- non-sample price snapshot records
- live availability evidence

Resolution can pass even when the live instance-type endpoint is inconclusive, but
only with an explicit warning that live availability is unknown until launch attempt.

Resolution fails closed when product catalog evidence is missing, prices are sample
data, price records are ambiguous, or operator shape confirmation is absent.

M029B keeps:

- `launch_ready=false`
- `launch_allowed=false`
- `billable_action_performed=false`
