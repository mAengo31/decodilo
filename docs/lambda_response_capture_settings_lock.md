# Lambda Response-Capture Settings Lock

M033 locks the response-capture settings required after the M029C and M031
launch response losses.

Required settings include:

- capture HTTP status before JSON parsing;
- capture redacted headers;
- capture content type and content length;
- capture body-size metadata;
- distinguish timeout, malformed JSON, non-JSON body, and empty body;
- keep secret redaction enabled.

Response body samples stay disabled by default. The lock is review-only and
keeps `launch_ready=false` and `launch_allowed=false`.
