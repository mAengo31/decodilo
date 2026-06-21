# Lambda Disabled Real Mutation Transport

M024 adds a real-mutation transport skeleton, but it is disabled by design. The
transport exists only to define the future code boundary for launch and
termination operations.

Every mutation-shaped method raises `LambdaRealMutationDisabledError` before:
- URL construction
- HTTP method construction
- request body construction
- credential access
- network access

The disabled report records `blocked_before_request_construction=true`,
`real_lambda_api_used=false`, `billable_action_performed=false`,
`real_mutation_enabled=false`, `launch_ready=false`, and `launch_allowed=false`.

This is not a Lambda launcher and not a termination implementation.

M025 treats this disabled transport as required evidence for final prelaunch
review. A passing disabled-launch test proves the skeleton raises before request
construction; it still does not approve execution.

M027 adds a minimal fake-server-only mutation path alongside this disabled
transport. The disabled real transport remains disabled and is not used for
fake execution. Real Lambda launch and termination methods still raise before
request construction.
