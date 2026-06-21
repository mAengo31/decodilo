# Lambda Live Read-Only Discovery

Milestone 019 introduces the first real Lambda Cloud API boundary, limited to
read/list/get discovery calls. A real API key may be used only through:

```bash
python -m decodilo.cli lambda live-discover \
  --api-key-file /path/to/lambda_api_key.txt \
  --live-read-only \
  --out /tmp/lambda-live-discovery.json
```

The key may have broad Lambda permissions, so Decodilo enforces read-only
behavior in code before transport:

- mutation guard must allow the operation
- endpoint policy must allow the GET endpoint
- only GET requests are constructed
- no request body is sent
- audit entries must show `mutation=false`

`live_api_used=true` means read-only discovery used the live API. It does not
mean launch readiness. Reports still keep `launch_ready=false` and
`launch_allowed=false`.

Milestone 019A extends this with endpoint calibration:

```bash
python -m decodilo.cli lambda live-discover \
  --api-key-file /path/to/lambda_api_key.txt \
  --live-read-only \
  --endpoint-set standard \
  --max-pages 10 \
  --max-items 1000 \
  --summary-out /tmp/lambda-live-summary.json \
  --redaction-mode local_private_report \
  --out /tmp/lambda-live-discovery.json
```

`--fail-on-partial` can turn unsupported or failed read endpoints into command
failure. Without it, partial failures are recorded in endpoint calibration and
the read-only audit can return `passed_with_read_failures`.
