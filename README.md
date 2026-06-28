# decodilo

`decodilo` is a safety-first Decoupled DiLoCo research scaffold and Lambda
Cloud lifecycle validation harness. It started as a CPU-only simulator for
distributed synchronization mechanics, and now also contains guarded Lambda
Cloud tooling for read-only discovery, one-instance lifecycle smoke tests,
metadata-only bootstrap, and SSH-connectivity diagnostics.
It now also tracks the first minimal remote-command milestone, limited to the
single no-op command `true`.

The core rule of the project is simple: make every expensive or risky action
explicit, reviewable, bounded, and reversible. Durable review artifacts stay
non-executable with `launch_ready=false` and `launch_allowed=false`; real
request sends require separate one-shot operator gates.

## Current Status

The local Decoupled DiLoCo side supports:

- CPU-only toy objective simulation.
- Local multiprocess learner/syncer runtime.
- Deterministic event logs, replay, checkpoints, and recovery artifacts.
- Chunked and binary tensor artifacts for large-state planning.
- Local-only scaling, budget, backend, and lifecycle planning.
- Optional CPU-capable torch adapter tests.

The Lambda Cloud side supports guarded validation only:

- Read-only live discovery through allowlisted GET endpoints.
- One-instance lifecycle launch and owned termination under explicit gates.
- Metadata-only bootstrap with no SSH and no remote commands.
- SSH-connectivity diagnostics and staged minimal remote-command validation.
- A successful no-op command stage using only `true`, with no stdout collection,
  no shell exploration, no file transfer, no port forwarding, no package
  installation, and no training.
- A successful first remote Decodilo runtime baseline that generated a bounded
  CI-profile report from uploaded source and local wheelhouse dependencies.
- A local/offline `dev tiny-smoke` command for the next future bounded remote
  Decodilo smoke review.
- A local/offline `dev runtime-smoke` command for the next future bounded
  runtime/protocol smoke review.
- Capacity closeout, spend audit, secret redaction, and post-run reconciliation
  artifacts.

No default test or default command launches Lambda, mutates Lambda resources,
uses SSH, installs packages, or trains a model.

## Latest Lambda Validation State

The most recent successful lifecycle milestone was M051B:

- Launched exactly one `gpu_8x_a100_80gb_sxm4` instance in `us-midwest-1`.
- Collected provider/API-visible metadata only.
- Did not SSH, run commands, install packages, transfer files, or train.
- Terminated the owned instance and verified a clean final provider state.
- Conservative spend audit remained below the $50 milestone budget.

The most recent remote-runtime milestone was M057:

- Launched exactly one `gpu_1x_a10` instance in `us-east-1`.
- Verified the instance reached `running`.
- Discovered the SSH host from provider metadata at `data[0].ip`.
- Verified TCP port 22 became reachable.
- Executed exactly one bounded SSH remote command: `true`.
- Did not open an interactive shell, collect stdout, run `nvidia-smi`, run
  remote `python`, transfer files, forward ports, install packages, or train.
- Terminated the owned instance and verified final discovery was clean.
- Historical M057 billable action occurred; M058 itself is offline-only and
  non-billable.

M058 closes out M057 as `ssh_noop_command_success`, reconciles the final
provider state, and defines the next remote-command stage policy. The next
future review is M059, an identity-command review currently limited to
`hostname`.

M059 then completed the first hostname-only identity-command run:

- Launched exactly one `gpu_1x_a10` instance in `us-east-1`.
- Discovered the SSH host from provider metadata at `data[0].ip`.
- Executed exactly one bounded SSH remote command: `hostname`.
- Captured stdout/stderr only through bounded redacted diagnostics.
- Did not run `whoami`, `nvidia-smi`, remote Python, shell exploration,
  command chaining, file transfer, port forwarding, package installation, or
  training.
- Terminated the owned instance and verified final discovery was clean.

M060 closes out M059 offline as `ssh_hostname_identity_success`, preserves the
evidence package, and records the next step as planning for a future M061
`whoami` identity-command review only. M060 does not authorize immediate launch
or command execution.

M071R completed the first remote Decodilo runtime baseline:

- Uploaded one sanitized source bundle and one sanitized dependency wheelhouse.
- Installed dependencies from the uploaded wheelhouse only.
- Ran exactly one Decodilo command:
  `dev ci-profile-report --out /tmp/decodilo-first-experiment-ci-profile-report.json`.
- Captured bounded artifact metadata and verified clean termination.
- Did not train, download data/models, use internet package installation, or
  run arbitrary shell commands.

M072 closes out M071R offline. M072A adds the local/offline `dev tiny-smoke`
command and authorizes only a future M073R tiny-smoke review. M072A itself does
not launch, SSH, upload, run remote commands, install packages, download, train,
or spend.

M073R2 completed the remote tiny-smoke run. M074 closes it out offline, and
M074A adds the local/offline `dev runtime-smoke` command for a future M075R
runtime/protocol smoke review. M074A itself does not call Lambda, SSH, upload,
run remote commands, install packages, download, train, or spend.

## Safety Invariants

The project intentionally separates standing review from execution:

- Standing artifacts remain durable and non-executable.
- Real launches require explicit operator confirmation and one-shot arming.
- Launch attempts are capped at one request send per approved run.
- Automatic launch retry is forbidden after response loss, malformed response,
  capacity rejection, or any HTTP 4xx/5xx response.
- Only owned instances may be terminated.
- Owned instances must be terminated in the same supervised run if created.
- Termination must be verified through read-only provider discovery/list/get.
- OS shutdown is not considered termination.
- Public reports must redact secrets, raw SSH key names, and sensitive host
  details where applicable.

For SSH-connectivity-only work:

- SSH may be used only for a bounded handshake/authentication probe.
- Interactive shells are forbidden.
- Remote commands are forbidden unless a later milestone explicitly authorizes
  one bounded command.
- `nvidia-smi`, remote `python`, and shell command collection are forbidden.
- `scp`, `sftp`, `rsync`, upload, and download are forbidden.
- Local, remote, dynamic, agent, and X11 forwarding are forbidden.
- Package installation, setup scripts, cloud-init, model download, data
  download, and training are forbidden.

For staged remote-command work:

- M057 accepted only `true`.
- M058 is offline closeout and future planning only.
- M059 may review only an identity command such as `hostname`.
- `nvidia-smi`, Python, shell exploration, package install, and training remain
  separate future stages and are not approved by M058.

See [docs/invariants.md](docs/invariants.md) for the fuller invariant set.

## Repository Layout

```text
src/decodilo/
  cli.py                         Main command-line entry point
  lambda_cloud/                  Lambda Cloud planning, gates, reports, probes
  local_runtime/                 Local learner/syncer runtime
  artifacts/                     Chunked and binary artifact support
  replay/                        Deterministic replay and validation
  scaling/                       Local scaling and budget estimators

tests/                           Unit, profile, and safety regression tests
docs/                            Milestone reports, policies, runbooks
```

Important Lambda documentation:

- [docs/lambda_m055_host_discovery_fix.md](docs/lambda_m055_host_discovery_fix.md)
- [docs/lambda_ssh_host_key_policy.md](docs/lambda_ssh_host_key_policy.md)
- [docs/lambda_ssh_identity_policy.md](docs/lambda_ssh_identity_policy.md)
- [docs/lambda_ssh_failure_classification.md](docs/lambda_ssh_failure_classification.md)
- [docs/lambda_ssh_live_candidate_selector.md](docs/lambda_ssh_live_candidate_selector.md)
- [docs/lambda_ssh_noop_command_success.md](docs/lambda_ssh_noop_command_success.md)
- [docs/lambda_remote_command_stage_policy.md](docs/lambda_remote_command_stage_policy.md)
- [docs/lambda_smallest_useful_command_review.md](docs/lambda_smallest_useful_command_review.md)
- [docs/lambda_m059_command_runbook.md](docs/lambda_m059_command_runbook.md)
- [docs/lambda_ssh_hostname_identity_success.md](docs/lambda_ssh_hostname_identity_success.md)
- [docs/lambda_m061_whoami_identity_decision.md](docs/lambda_m061_whoami_identity_decision.md)
- [docs/lambda_metadata_bootstrap_success.md](docs/lambda_metadata_bootstrap_success.md)
- [docs/lambda_metadata_bootstrap_closeout.md](docs/lambda_metadata_bootstrap_closeout.md)
- [docs/lambda_tiny_smoke.md](docs/lambda_tiny_smoke.md)
- [docs/lambda_m073r_tiny_smoke_runbook.md](docs/lambda_m073r_tiny_smoke_runbook.md)
- [docs/lambda_runtime_smoke.md](docs/lambda_runtime_smoke.md)
- [docs/lambda_m075r_runtime_protocol_smoke_runbook.md](docs/lambda_m075r_runtime_protocol_smoke_runbook.md)
- [docs/lambda_synthetic_experiment.md](docs/lambda_synthetic_experiment.md)
- [docs/lambda_m077r_first_synthetic_experiment_runbook.md](docs/lambda_m077r_first_synthetic_experiment_runbook.md)

## Install

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Optional torch tests require the torch extra:

```bash
pip install -e '.[torch]'
```

## Local Simulation

Run a CPU-only simulation:

```bash
python -m decodilo.cli simulate \
  --learners 4 \
  --steps 200 \
  --min-quorum 2 \
  --seed 123 \
  --report-json /tmp/decodilo-report.json
```

The simulator optimizes a toy convex objective with independent learner islands
and syncer-side token-weighted merges. It does not allocate GPUs or use cloud
APIs.

## Local Runtime

Run the localhost-only multiprocess runtime:

```bash
python -m decodilo.cli local run \
  --learners 4 \
  --steps 200 \
  --min-quorum 2 \
  --seed 123 \
  --workdir /tmp/decodilo-local
```

The local runtime uses learner subprocesses, a syncer process, JSONL-over-TCP
transport envelopes, idempotent fragment submission, heartbeats, replay
validation, and checkpoint/recovery artifacts.

## Lambda Read-Only Discovery

Read-only Lambda discovery is the only live Lambda operation that should be
run without a separate launch milestone. It requires `.env` credentials and is
GET-only:

```bash
python -m decodilo.cli lambda live-discover \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --live-read-only \
  --endpoint-set standard \
  --max-pages 10 \
  --max-items 1000 \
  --out /tmp/decodilo-lambda-readonly-discovery.json \
  --summary-out /tmp/decodilo-lambda-readonly-summary.json \
  --redaction-mode local_private_report
```

Real launch/terminate commands are intentionally not documented here as casual
copy-paste commands. Use the generated milestone runbook previews and one-shot
arming artifacts for supervised live runs.

## Credentials

Never commit `.env`, private keys, provider tokens, or raw key material.

Typical local `.env` values are:

- `LAMBDA_API_KEY` for Lambda Cloud API access.
- `CONFIRM_LAMBDA_BILLABLE_ACTION=true` only for explicitly approved live
  billable runs.
- `LAMBDA_SSH_KEY` or an SSH private key reference, depending on the active
  SSH credential policy.

The code must not print secrets. Public artifacts should use hashes, redaction,
or field-name summaries instead of raw values.

## Test Commands

Focused M057/M058 remote command regressions:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q \
  tests/test_lambda_m057_minimal_remote_command.py \
  tests/test_lambda_ssh_noop_command_success_record.py \
  tests/test_lambda_ssh_noop_command_reconciliation.py \
  tests/test_lambda_ssh_noop_command_evidence_package.py \
  tests/test_lambda_ssh_noop_command_closeout.py \
  tests/test_lambda_remote_command_stage_policy.py \
  tests/test_lambda_smallest_useful_command_review.py \
  tests/test_lambda_m059_remote_command_authorization.py \
  tests/test_lambda_m059_command_runbook_preview.py \
  tests/test_lambda_m058_report.py \
  tests/test_cloud_still_disabled_m058.py \
  -o cache_dir=/tmp/decodilo-pytest-cache-m58-focused
```

Quick profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q \
  -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" \
  -o cache_dir=/tmp/decodilo-pytest-cache-quick
```

Full suite:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q \
  -o cache_dir=/tmp/decodilo-pytest-cache-full
```

Lint:

```bash
RUFF_CACHE_DIR=/tmp/decodilo-ruff-cache ruff check .
```

Optional torch tests:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  tests/test_torch_causal_lm_optional.py \
  tests/test_torch_runtime_local_optional.py \
  -q \
  -o cache_dir=/tmp/decodilo-pytest-cache-torch
```

## Development Workflow

For ordinary code changes:

1. Keep diffs small and behavior-preserving unless the milestone requires a
   behavior change.
2. Add or update tests beside the safety or runtime surface being changed.
3. Run the focused tests for the touched behavior.
4. Run the quick profile.
5. Run `ruff check .`.
6. Do not run live Lambda commands unless the current milestone explicitly
   authorizes them and all gates are present.

For Lambda work, preserve these reporting fields unless a milestone explicitly
changes the schema:

- `launch_ready=false`
- `launch_allowed=false`
- `billable_action_performed=false` for planning/offline milestones
- `remote_command_attempted=false`
- `file_transfer_attempted=false`
- `port_forwarding_attempted=false`
- `package_install_attempted=false`
- `training_attempted=false`

## Current Recommended Next Milestone

M063 completed successfully and M064 is the offline closeout/planning milestone.
The next safe remote-runtime milestone is M065, a supervised Python runtime
version query-only run. It should:

- freshen read-only Lambda discovery,
- select a live available candidate,
- launch exactly one instance,
- discover host metadata and wait for TCP/22 readiness,
- execute only `python3 --version`,
- capture bounded redacted stdout/stderr only,
- avoid interactive shell, inline Python, scripts, imports, command chaining,
  package installation, file transfer, forwarding, setup scripts, cloud-init, and
  training,
- terminate the owned instance,
- verify clean post-run discovery.

Training remains out of scope.
### Lambda M067S Remote Vertical-Slice Closeout

M067S closes the M067R source-bundle vertical-slice attempt as a safe pre-manifest SSH/TCP readiness failure. M067R launched and terminated cleanly, but TCP/22 never became reachable, so SSH, bundle upload, and Decodilo manifest commands were not attempted.

Future Decodilo vertical-slice retries now prefer SSH-proven candidate/region pairs, currently `gpu_1x_a10` in `us-east-1`, and exclude recent TCP/22 failures such as `gpu_1x_h100_sxm5` in `us-south-2` by default. M067S itself is offline only and keeps `launch_ready=false` and `launch_allowed=false`.

### Lambda M068W Dependency Wheelhouse Prep

M068W prepares a Linux/Python 3.10-compatible wheelhouse for a future
dependency-bundle retry after M067R3 reached source import but failed CLI startup
on missing `pydantic`. It is local-only: no Lambda calls, SSH, uploads, remote
commands, Lambda-side installs, or spend.

Controlled wheel downloads, when explicitly approved, run only on the
development machine with binary wheels, CPython 3.10, and manylinux x86_64
constraints. Future Lambda runs must install only from the uploaded local
wheelhouse using `--no-index` or equivalent local-only behavior.

### Lambda M076A Synthetic Experiment Command

M076A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev synthetic-experiment \
  --synthetic \
  --max-steps 1 \
  --out /tmp/decodilo-synthetic-experiment.json
```

The command uses only synthetic in-memory runtime/protocol data. It performs no
network access, package installation, data/model download, or real model
training, and it requires neither torch nor GPU. It writes one bounded JSON
report and keeps `launch_ready=false` and `launch_allowed=false`.

M076A may authorize only a future supervised M077R first synthetic experiment
review. That future milestone must still pass fresh gates and operator
confirmation before any live Lambda action.

### Lambda M078A Learner/Syncer Smoke Command

M078A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev learner-syncer-smoke \
  --synthetic \
  --max-steps 1 \
  --out /tmp/decodilo-learner-syncer-smoke.json
```

The command uses only synthetic in-memory learner/syncer/protocol data. It
performs no network access, package installation, data/model download, or real
model training, and it requires neither torch nor GPU. It writes one bounded
JSON report and keeps `launch_ready=false` and `launch_allowed=false`.

M078A may authorize only a future supervised M079R next synthetic experiment
review. That future milestone must still pass fresh gates and operator
confirmation before any live Lambda action.

### Lambda M080A DiLoCo-Shaped Smoke Command

M080A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-smoke.json
```

The command uses only synthetic in-memory DiLoCo-shaped learner/syncer protocol
data. It performs no network access, package installation, data/model download,
or real model training, and it requires neither torch nor GPU. It reports the
current fidelity honestly as `diloco_shaped_protocol_only`, not full DiLoCo
optimizer fidelity, because the active path does not run true inner AdamW plus
outer Nesterov semantics.

M080A may authorize only a future supervised M081R DiLoCo-shaped synthetic
review. That future milestone must still pass fresh gates and operator
confirmation before any live Lambda action.

### Lambda M082A DiLoCo Optimizer-Fidelity Smoke Command

M082A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev diloco-optimizer-smoke \
  --synthetic \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-optimizer-smoke.json
```

The command uses only deterministic synthetic vector data. It performs no
network access, package installation, data/model download, or real model
training, and it requires neither torch nor GPU. It validates a tiny AdamW
inner step, pseudo-gradient construction, Nesterov outer update, optimizer state
roundtrip, and strict reference-value check. It does not claim full DiLoCo
training or parameter-fragment semantics.

M082A may authorize only a future supervised M083R optimizer-fidelity smoke
review. That future milestone must still pass fresh gates and operator
confirmation before any live Lambda action.

### Lambda M084A Integrated DiLoCo Smoke Command

M084A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev integrated-diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-integrated-diloco-smoke.json
```

The command uses deterministic synthetic in-memory vectors and local
learner/syncer protocol mechanics. It performs no network access, package
installation, data/model download, or real model training, and it requires
neither torch nor GPU. It verifies one bounded integration of protocol update,
pseudo-gradient construction, AdamW semantics, Nesterov semantics, optimizer
state roundtrip, and replay/metric validation.

The report may claim `integrated_optimizer_protocol_smoke`, but it must not
claim full DiLoCo training or parameter-fragment semantics.

### Lambda M086A Parameter-Fragment Smoke Command

M086A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev parameter-fragment-smoke \
  --synthetic \
  --fragments 2 \
  --max-steps 1 \
  --out /tmp/decodilo-parameter-fragment-smoke.json
```

The command uses deterministic synthetic vector data only. It performs no
network access, package installation, data/model download, or real model
training, and it requires neither torch nor GPU. It splits one tiny vector into
two fragments, applies one deterministic fragment update, validates
per-fragment versions and state roundtrip, reconstructs the full vector, and
checks strict reference values.

The report may claim `parameter_fragment_semantics=synthetic_vector_fragments`,
but it must not claim true model/layer fragmentation, communication overlap,
quantized communication, real model training, or full Streaming DiLoCo.

M086A may authorize only a future supervised M087R parameter-fragment smoke
review. That future milestone must still pass fresh gates and operator
confirmation before any live Lambda action.

### Lambda M088A Bounded Synthetic DiLoCo Experiment Command

M088A adds the local/offline bounded command:

```bash
python -m decodilo.cli dev bounded-diloco-experiment \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --fragments 2 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-bounded-diloco-experiment.json
```

The command uses deterministic synthetic in-memory vector data only. It performs
no network access, package installation, data/model download, or real model
training, and it requires neither torch nor GPU. It combines one learner/syncer
protocol round, AdamW inner semantics, pseudo-gradient construction, Nesterov
outer semantics, two synthetic vector fragments, replay/metric validation, and
strict reference-value checks in one bounded artifact.

The report may claim `optimization_fidelity=bounded_synthetic_diloco_experiment`
only for that tiny synthetic experiment. It must not claim paper-scale DiLoCo,
real model training, true model/layer fragmentation, communication overlap, or
quantized communication.

M088A may authorize only a future supervised M089R bounded experiment review.
That future milestone must still pass fresh gates and operator confirmation
before any live Lambda action.

### Lambda M092 Tiny Real Training Smoke Command

M092 adds the local/offline tiny real-training command:

```bash
python -m decodilo.cli dev tiny-real-training-smoke \
  --synthetic \
  --model tiny-linear \
  --steps 1 \
  --optimizer adamw \
  --out /tmp/decodilo-tiny-real-training-smoke.json
```

The command uses deterministic synthetic in-memory data and pure-Python
arithmetic. It creates a tiny linear model, runs one forward/loss/gradient
calculation, applies one AdamW update, validates optimizer state, and checks
deterministic replay. It performs no network access, package installation,
dataset/model download, GPU work, long-running training, or background process.

The report may claim tiny real training mechanics only. It must not claim real
model-scale training, dataset pipeline validation, distributed DiLoCo training,
or paper-scale DiLoCo. M092 may authorize only a future supervised M093R review;
that future milestone still requires fresh gates and operator confirmation
before any live Lambda action.
