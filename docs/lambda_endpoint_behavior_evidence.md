# Lambda Endpoint Behavior Evidence

Endpoint behavior evidence is derived only from an ingested support/operator
response. It records the confirmed launch and terminate method/path, expected
success statuses, response content types, instance ID field or async/no-ID
semantics, terminate terminal states, and list/discovery behavior.

After three ambiguous launch outcomes, missing launch/terminate method/path or
missing ambiguous-response guidance blocks endpoint confidence upgrade.

Evidence commands are offline and review-only:

```bash
python -m decodilo.cli lambda support-confirmation endpoint-behavior \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --out /tmp/decodilo-lambda-endpoint-behavior-evidence.json
```

This evidence does not authorize launch.
