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

## Milestone 018 Lambda API Boundary

The Lambda Cloud API boundary is fixture-backed only. `DisabledLambdaCloudClient`
raises for all operations, and `ReadOnlyLambdaCloudClient` can only read from a
local fake transport. Lambda launch and teardown plans are informational dry-run
artifacts, and execution raises `LaunchDisabledError`.

No M018 command accepts a raw API key, no Lambda module reads Lambda credential
environment variables, and no Lambda module opens a real network path.

## Milestone 019 Read-Only Lambda API

M019 adds live read-only discovery but still no launcher. The only live Lambda
command is `lambda live-discover`, which requires `--live-read-only` and an
explicit `--api-key-file`. The live transport only builds GET requests after
mutation guard and endpoint policy approval.

## Milestone 020 Read-Only Reconciliation

M020 reconciles read-only discovery, price snapshots, dry-run launch plans,
teardown plans, ledgers, and human approval manifests. It adds no launcher and
no mutation-capable Lambda client behavior. The approval gate may mark a future
fake launch lifecycle as a review candidate, but real launch remains blocked by
disabled launch code and milestone policy.

## Milestone 021 Fake Lifecycle Rehearsal

M021 adds a fake launch/teardown lifecycle executor that operates only on local
JSON state and synthetic `fake-*` resource IDs. It is a mutation safety rehearsal,
not a launcher. Fake lifecycle commands do not accept live credentials, do not
use the Lambda API, and cannot create, terminate, restart, or delete real cloud
resources.

## Milestone 022 Fake Mutation Harness

M022 adds fake mutation-shaped request/response models and an in-memory fake
transport for local lifecycle stress. The live Lambda client and transport remain
read-only; no real POST/PUT/PATCH/DELETE Lambda transport is added.

## Milestone 023 Real Mutation Boundary Review

M023 adds proposal, operation spec, arming gate, kill-switch design, termination
verification policy, safety case, evidence package, and review record artifacts.
These are review-only documents and JSON models. They do not add a real Lambda
mutation transport or launcher.

## Milestone 024 Disabled Mutation Skeleton

M024 adds the disabled real-mutation transport skeleton and executable-path
proof. Mutation-shaped methods exist only as future boundary definitions and
raise before URL, method, body, credential, or network construction. Feature
flags, arming state, request builder, budget lock, idempotency plan, resource
scope, skeleton client, skeleton audit, and preflight integration all keep
`real_mutation_enabled=false`, `launch_ready=false`, and
`launch_allowed=false`.

## Milestone 025 Final Prelaunch Review

M025 consumes M019C through M024 evidence and produces a final prelaunch
evidence package, runbooks, operator checklist, spend/resource/secret reviews,
semantic no-mutation audit, and go/no-go design record. The highest positive
status is `go_for_future_m026_real_launch_review`. It is not launch approval and
does not add executable mutation code.

## Milestone 026 Decision Gate

M026 consumes M019C through M025 evidence and a human review manifest to decide
whether M027 may implement minimal real Lambda mutation code disabled by
default. It may authorize implementation scope only; it cannot enable launch,
termination, or spend.

The blocker matrix always retains launch-execution blockers for current policy
and missing executable launch code. Preflight reports the M026 decision and M027
authorization status, but keeps `real_mutation_enabled=false`,
`launch_ready=false`, and `launch_allowed=false`.

## Milestone 027 Fake-Server-Only Minimal Mutation Path

M027 implements minimal launch and terminate request construction and executes
the flow only against a local fake server or in-memory fake transport. The path
requires M027 authorization, endpoint policy, mutation guard, budget lock,
idempotency, resource scope, teardown, and termination verification evidence.

Real Lambda URLs and credentials are rejected before execution. The live Lambda
client remains read-only, and preflight keeps `real_mutation_enabled=false`,
`launch_ready=false`, and `launch_allowed=false`.

## Milestone 028 Final M029 Authorization Package

M028 produces final review locks and authorization artifacts for a future M029
one-instance launch attempt. It may refresh read-only Lambda state if explicitly
given an env file, but it cannot mutate resources.

Budget, resource, launch-window, teardown verification, operator confirmation,
and no-mutation audit artifacts are required before the M029 authorization
package can pass. That package authorizes the next milestone only; M028 remains
non-launchable and keeps `real_mutation_enabled=false`, `launch_ready=false`,
and `launch_allowed=false`.

## Milestone 029 First Billable Attempt

M029 may use the first narrowly scoped real mutation path. It is limited to one
launch request, read-only verification, one owned-instance terminate request,
and read-only termination verification. Restart, create/delete, SSH, setup
scripts, training, background execution, and unowned termination remain
forbidden.

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

## M029D Incident Gate

After a lost M029 launch response, future launch preflight must reject another
launch while the incident is open or unresolved. Closeout requires read-only
discovery comparison, owned-instance reconciliation, and explicit manual Lambda
console confirmation. Automation must not terminate ambiguous or unowned
instances.
