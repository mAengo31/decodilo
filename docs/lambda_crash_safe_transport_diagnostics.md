# Lambda Crash-Safe Transport Diagnostics

Crash-safe diagnostics ensure Lambda mutation transport failures are persisted
before process exit.

For every launch or owned-terminate transport failure, the runtime must persist:

- whether the request was sent;
- HTTP status, reason, content type, content length, and body size when known;
- response classification;
- redacted exception type/message;
- elapsed seconds;
- manual review requirement;
- `no_auto_retry=true`;
- secret scan status.

The diagnostics are evidence only. They do not launch, terminate, retry, or
authorize a future launch.
