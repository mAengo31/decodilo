# Lambda Support Confirmation Request

M036 generates a structured, secret-free request for Lambda support or an
operator who has verified Lambda API documentation.

The request asks for launch and terminate method/path, request fields, response
status/content type/body shape, instance ID semantics, ambiguous response
behavior, idempotency/client-token behavior, list/get verification behavior,
quota/usage endpoint support, rate limits, and the safest lower-cost lifecycle
smoke shape.

The command is review-only:

```bash
python -m decodilo.cli lambda support-confirmation request \
  --out /tmp/decodilo-lambda-support-confirmation-request.json
```

It performs no Lambda API call, sends no mutation request, and keeps
`launch_ready=false` and `launch_allowed=false`.
