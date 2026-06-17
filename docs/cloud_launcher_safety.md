# Cloud Launcher Safety

Milestone 007 defines the launcher interface but intentionally ships only a
disabled launcher. Real cloud launch remains impossible.

## Disabled Launcher

`DisabledCloudLauncher.launch(...)` always raises `LaunchDisabledError`.
`DisabledCloudLauncher.teardown(...)` also raises because no live resources
exist in this milestone.

The disabled launcher:

- does not call Lambda APIs
- does not read credentials
- does not shell out to provider CLIs
- does not create subprocess cloud launch paths
- does not perform network calls

## Launch Review Checklist

`cloud launch-review` reads a dry-run plan and writes a checklist. The checklist
keeps `launch_allowed=false` and includes gates for:

- launch disabled status
- budget manifest presence
- teardown plan presence
- operator acknowledgement
- public bind disabled
- dry-run validation errors absent

Operator acknowledgement defaults to false. That means a generated review can
be valid as an artifact while still failing as an approval gate.

## Teardown Plan

Dry-run plans include an informational `TeardownPlan` with expected future
teardown steps, required identifiers, and max runtime. It must not contain live
resource IDs:

```text
has_live_resource_ids = false
live_resource_ids = []
```

Future real launch work must add live resource tracking before launch is
allowed.

## Future Requirements

Before enabling a real Lambda launcher, the project must add explicit
credential handling, live availability checks, launch supervision, provider
resource IDs, teardown verification, audit logs, hard budget gating, and a
review flow that changes `launch_allowed` only after all gates pass.

## Launch Preflight

Milestone 008 adds local and cloud preflight commands. Cloud preflight checks a
dry-run plan, launch review checklist, teardown plan, budget identifiers,
artifact hashes, disabled launcher status, and scaling estimates when present.
It still reports `launch_allowed=false` and cannot call a provider API.

Preflight is a launch gate, not a launcher. A passing cloud preflight means the
dry-run artifacts are internally consistent; it does not mean resources can be
created.
