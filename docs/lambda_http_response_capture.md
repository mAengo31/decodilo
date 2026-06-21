# Lambda HTTP Response Capture

`LambdaHTTPResponseCapture` records safe response metadata for future Lambda
launch and terminate diagnostics.

Captured metadata includes status code before JSON parsing, redacted headers,
content type, content length, body size, a body hash prefix, elapsed time, and
redacted exception details. Body samples are disabled by default and are size
limited when explicitly enabled.

The capture model classifies timeout, connection error, empty success body,
non-JSON success body, HTTP JSON error, HTTP non-JSON error, malformed JSON, and
schema validation failure. It never stores Authorization headers or API keys.
