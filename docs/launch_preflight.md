# Launch Preflight

Milestone 008 adds local and cloud preflight checks. This is still not a
launcher.

## Local Preflight

```bash
python -m decodilo.cli preflight local \
  --workdir /tmp/decodilo-run
```

Local preflight checks:

- `run_spec.json` exists and loads
- `artifacts.json` exists
- artifact hashes validate
- report metric validation passes when a report exists
- runtime resource settings are visible

## Cloud Preflight

```bash
python -m decodilo.cli preflight cloud \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-preflight.json
```

Cloud preflight checks:

- dry-run plan validation
- `launch_allowed=false`
- budget manifest presence
- snapshot and record identifiers
- teardown plan with no live resource IDs
- launch review checklist
- optional local workdir artifacts
- scaling estimates when present

The output separates these booleans:

- `preflight_passed`: the dry-run preflight artifact checks completed without
  errors.
- `safety_checks_passed`: dry-run cloud safety checks passed.
- `artifact_checks_passed`: referenced local artifacts, when supplied, passed
  hash checks.
- `budget_checks_passed`: the dry-run plan includes a budget manifest and
  budget fields.
- `launch_review_passed`: the launch review approval gate passed. This is
  normally false because operator acknowledgement defaults to false.
- `launch_ready`: always false in this milestone.
- `launch_allowed`: always false in this milestone.

Cloud preflight always includes the warning:

```text
cloud launch is disabled in this build
```

It may report warnings for missing scaling estimates or other planning gaps, but
it does not call cloud APIs and cannot launch.

Milestone 010 adds binary artifact mode awareness. Preflight reports
`tensor_artifact_codec`, `fragment_artifact_codec`, `checkpoint_artifact_codec`,
`artifact_backend="local_filesystem"`, and `remote_backend_enabled=false`.
Large expected model-state plans should use `binary_v1` and chunked modes;
inline or JSON-safe large-state configs produce warnings or failures according
to policy.

Large expected model state adds runtime-mode checks. Inline-only payload
storage, inline-only global updates, and inline-only checkpoints are rejected or
warned when the expected state exceeds the configured inline threshold. Cloud
preflight also warns that artifact transport is local shared filesystem only and
that no remote artifact backend exists.

## Milestone 012 Lifecycle Checks

Local preflight now checks lifecycle state for completed chunked runs:

- artifact manifest exists and hashes verify
- recovery manifest exists and validates
- latest checkpoint inputs referenced by the recovery manifest exist
- report metric validation passes when a report is present
- a dry-run artifact GC plan can be produced

Cloud preflight continues to warn that the remote artifact backend is disabled,
local retention policy is not a cloud retention policy, there is no live
availability check, and cloud launch is disabled. `launch_ready` and
`launch_allowed` remain false.

## Milestone 013 Lifecycle Checks

Local preflight now also runs artifact-reference audit, recovery-manifest chain
validation, failed-GC-transaction checks, and lifecycle warnings for segmented
runs without a recent replay snapshot. These checks improve local run safety;
they do not imply cloud launch readiness.
