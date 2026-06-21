# Lambda Launch Transport Diagnostics

Launch transport diagnostics are review-only evidence for response-loss
analysis.

They record:

- timeout configuration;
- request-sent timestamp if available;
- exception type;
- HTTP status if available;
- redacted response headers;
- response content type;
- response body size;
- whether the failure was timeout, malformed response, HTTP error, transport
  error, or unknown.

Diagnostics must not store raw secrets, raw Authorization headers, or raw
response bodies. They do not perform network requests and cannot enable launch.

M032 extends the transport boundary with `LambdaHTTPResponseCapture`, which
records status before JSON parsing and classifies timeout, empty body, non-JSON
body, malformed JSON, schema validation failure, and HTTP error responses.
Authorization headers and bearer tokens are redacted.

M033 locks these capture settings for a future M034 review. The lock keeps body
sampling disabled by default and requires secret redaction to remain enabled.
