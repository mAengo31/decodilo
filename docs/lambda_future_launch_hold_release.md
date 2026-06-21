# Lambda Future Launch Hold Release

The M031 repeated-response-loss hold can be released only for future review, not
for launch execution.

Release requires the M031 incident to be closed, response-loss mitigation to be
accepted, endpoint spec confidence to be medium or high, no automatic relaunch
policy to remain enforced, and fresh operator reapproval before any future
attempt.

Hold release reports keep `launch_ready=false` and `launch_allowed=false`.

M033 can use a released hold as one input to a future M034 authorization record,
but that record is still review-only. It does not permit launch execution.
