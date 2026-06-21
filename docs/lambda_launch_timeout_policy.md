# Lambda Launch Timeout Policy

M033 records the timeout policy for a future M034 launch attempt.

The default launch and terminate request timeouts are 30 seconds, longer than the
prior 0.16-0.36 second response-loss windows. Read-only verification has a
longer timeout window for reconciliation.

Automatic launch retry after response loss is forbidden. Unknown ownership
requires manual review. This policy cannot enable launch.
