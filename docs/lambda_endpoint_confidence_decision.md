# Lambda Endpoint Confidence Decision

M037 converts validated support evidence into an endpoint confidence decision.

High confidence requires confirmed launch and terminate method/path, launch
success status and body shape, instance ID or async/no-ID semantics, ambiguous
launch timeout behavior, termination verification behavior, and rate-limit
answers or explicit accepted unknowns.

If support evidence contradicts the current implementation path or method, M037
records `endpoint_behavior_contradicts_current_implementation` and future launch
work must fix the implementation before any new attempt.

This decision never emits `launch_ready=true` or `launch_allowed=true`.
