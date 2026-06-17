# Cloud Dry Run

Milestone 006 adds Lambda cloud planning, not Lambda execution.

The dry-run planner:

- reads a local price snapshot
- checks freshness and sample-data policy
- checks budget and safety buffer
- selects advisory Lambda shape metadata
- writes a JSON plan
- always sets `launch_allowed=false`

It does not call Lambda APIs, read credentials, shell out to provider CLIs, or
launch instances.

Milestone 007 adds a disabled launcher interface, launch review checklist, and
dry-run teardown plan. These artifacts make the future launch boundary
auditable while keeping real launch impossible.

## Price Snapshots

Prices must come from `PriceSnapshot` data. The shape catalog contains no
prices. Sample and stale snapshots are rejected by default unless explicitly
allowed with CLI flags.

## Shape Catalog

`LambdaShapeCatalog` is planning metadata only. It is not live availability.
Live availability must wait for a future explicit API integration and must keep
the same budget and replay safeguards.

## Safety Checks

Dry-run plans include checks for:

- fresh price data unless stale prices are allowed
- non-sample data unless sample prices are allowed
- positive node count, GPU count, and runtime
- max run budget
- safety-buffer-adjusted cost within credits
- no secret values embedded in the plan
- no API client configured
- dry-run-only launch denial

## CLI

```bash
python -m decodilo.cli cloud dry-run lambda \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --nodes 1 \
  --hours 2 \
  --credits 7500 \
  --max-run-budget 1000 \
  --region us-west-1 \
  --out /tmp/decodilo-cloud-dry-run.json
```

Validate a plan:

```bash
python -m decodilo.cli cloud dry-run validate /tmp/decodilo-cloud-dry-run.json
```

Write a launch review checklist:

```bash
python -m decodilo.cli cloud launch-review \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json \
  --out /tmp/decodilo-launch-review.json
```

Prove the disabled launcher refuses launch:

```bash
python -m decodilo.cli cloud launch-disabled-test \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json
```

Dry-run plans include a `teardown_plan` with no live resource IDs. The launch
review gate remains failed by default because operator acknowledgement is false
and `launch_allowed` is forced false.

## Future Launcher Requirements

A real launcher must add explicit credentials handling, provider API clients,
live availability checks, startup supervision, teardown, audit logs, and hard
budget gates. It must not bypass `RunBudgetManifest`, price provenance,
RunSpec, artifact manifests, replay validation, or metric validation.
