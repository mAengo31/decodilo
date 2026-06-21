# Lambda Test Profiles

Lambda tests are split by execution risk.

## Offline

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "lambda_offline and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-lambda-offline
```

This profile covers fixture parsing, fake transports, fake server launch flows,
response capture, capacity closeout, selectors, gate checks, Strand payload
compatibility, and lifecycle evidence. It must not require `.env`, real
credentials, live Lambda reads, or Lambda mutations.

Generated milestone-history tests should be marked `launch_history_heavy` in
addition to `lambda_offline` and must stay out of quick unless they are the
single representative smoke test for that behavior.

## Manual Live Read-Only

`lambda_live` is reserved for manual real read-only discovery checks and must
not run by default. Tests in this profile require explicit operator control and
must never include mutation.

## Manual Real Mutation

`lambda_real_mutation` is manual-only. Real launch/terminate attempts belong in
the guarded CLI/operator milestone flow, not in default pytest.
