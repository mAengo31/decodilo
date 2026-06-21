# Lambda Live Discovery Calibration

Milestones 019A and 019C calibrate the live Lambda read-only discovery
boundary. They may use a real Lambda API key only when an operator explicitly
provides either `--api-key-file` or `--env-file .env --env-key LAMBDA_API_KEY`
together with `--live-read-only`.

This is not a launch milestone. The live discovery command only attempts
allowlisted GET endpoints, records endpoint coverage and response-shape
evidence, and writes a read-only report. It does not launch, terminate,
restart, create, delete, SSH, run setup scripts, train, or spend.

The standard protocol is:

```bash
python -m decodilo.cli lambda live-discover \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --live-read-only \
  --endpoint-set standard \
  --max-pages 10 \
  --max-items 1000 \
  --out /tmp/decodilo-lambda-live-discovery.json \
  --summary-out /tmp/decodilo-lambda-live-summary.json \
  --redaction-mode local_private_report

python -m decodilo.cli lambda audit-read-only \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --out /tmp/decodilo-lambda-read-only-audit.json

python -m decodilo.cli lambda live-ledger reconcile \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --out /tmp/decodilo-lambda-live-ledger.json

python -m decodilo.cli lambda live-preflight \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --read-only-audit /tmp/decodilo-lambda-read-only-audit.json \
  --ledger /tmp/decodilo-lambda-live-ledger.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --out /tmp/decodilo-lambda-live-preflight.json
```

Partial read failures are calibration evidence. They are recorded in endpoint
results and audit warnings unless `--fail-on-partial` is provided. Any mutation,
non-GET request, secret leak, missing teardown plan, or billable action fails
preflight.

For the `standard` endpoint set, `list_instance_types` and `list_instances` are
required read endpoints. Regions, images, SSH keys, filesystems, quota, and
usage are optional standard endpoints. A 404 for quota or usage is classified as
`unsupported_optional_endpoint`, which produces a warning but does not by itself
fail read-only preflight.

Reports always keep `billable_action_performed=false`,
`mutating_operations=0`, `launch_ready=false`, and `launch_allowed=false`.

M020 consumes this evidence for price/resource reconciliation and approval
planning. M020 does not make additional Lambda API calls; it reads the discovery
report, audit report, ledger, dry-run launch plan, teardown plan, price
snapshot, and optional approval manifest.
