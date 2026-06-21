# Lambda Repeated Response Loss Review

Repeated response-loss review is required after two real launch attempts sent a
launch request but did not receive a launch response.

The review consumes:

- M029C launch report;
- M031 launch report;
- M029E closeout;
- M031D closeout;
- transport diagnostics;
- endpoint diagnostics.

Two response-loss events activate a future-launch hold until mitigation is
accepted. Required mitigations include recording HTTP status before parsing,
capturing redacted response metadata, distinguishing timeout from malformed
responses, verifying endpoint path and method, and adding parser fixtures from
redacted provider responses where possible.

The review cannot enable launch. `launch_ready=false` and `launch_allowed=false`
remain invariant.

M032 adds mitigation acceptance evidence: HTTP status is captured before parsing,
redacted response metadata is recorded, fake regression fixtures cover timeout,
empty body, non-JSON body, malformed/schema failure, and HTTP error cases, and
future launch hold release is allowed only for future review.

M033 consumes that mitigation evidence for a third-attempt review package. It
requires endpoint-spec operator confirmation, response-capture settings lock,
timeout policy, correlation planning, and reconciliation planning before any
future M034 review can be authorized.
