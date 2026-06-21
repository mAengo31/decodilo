# Scavenged Compute

Scavenged compute models temporary or discounted learner pods. It is useful for
planning spot/preemptible, opportunistic, or otherwise unreliable learners without
implementing any real remote executor.

The estimate accounts for:

- expected extra learners
- availability window
- preemption rate
- startup time
- discount versus base cost
- churn events
- artifact pressure increase
- checkpoint pressure increase
- trust and data-access warnings

High preemption or startup time can erase the value of discounted capacity. Trust and
data-tier warnings are intentionally conservative because no remote storage or cloud
execution path exists yet.

