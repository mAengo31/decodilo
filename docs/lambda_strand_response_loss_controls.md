# Lambda Strand Response-Loss Controls

M037R checks that the lower-cost Strand path still satisfies the response-loss
controls added after the ambiguous launch attempts.

Required controls:

- Timeout at least 30 seconds.
- HTTP status captured before parse.
- Redacted headers, content type, and body-size metadata captured.
- Body samples disabled.
- No automatic launch retry.
- Launch parser accepts `data.instance_ids`.
- Terminate path accepts successful 2xx empty response bodies.
- Error parser accepts `error.message`.
- Launch payload contains no setup, cloud-init, or user-data fields.

```bash
python -m decodilo.cli lambda strand response-loss-controls \
  --out /tmp/decodilo-lambda-strand-response-loss-controls.json
```

This is an offline check and performs no Lambda mutation.

M038 lower-cost gate-check requires these controls to pass before future M039
can be reviewed.
