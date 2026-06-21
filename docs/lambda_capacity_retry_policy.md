# Lambda Capacity Retry Policy

Capacity errors are not response-loss incidents and are not teardown failures.
They indicate Lambda rejected the selected capacity before an owned instance was
created.

Policy:

- no immediate automatic retry
- no same-shape retry without fresh availability evidence
- availability-first selection is required for lifecycle smoke follow-up
- wait-and-retry may be recorded only for a future review with operator risk
  acceptance
- every future launch still needs a separate supervised milestone

The policy never sets `launch_ready=true` or `launch_allowed=true`.
