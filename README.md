# decodilo

`decodilo` is a safety-first Decoupled DiLoCo research scaffold and Lambda
Cloud lifecycle validation harness. It started as a CPU-only simulator for
distributed synchronization mechanics, and now also contains guarded Lambda
Cloud tooling for read-only discovery, one-instance lifecycle smoke tests,
metadata-only bootstrap, and SSH-connectivity diagnostics.

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
- SSH-connectivity-only diagnostics with no shell, no command execution, no
  file transfer, no port forwarding, no package installation, and no training.
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

The most recent SSH-connectivity milestone was M056:

- Launched exactly one live-selected `gpu_1x_a10` instance in `us-east-1`.
- Verified the instance reached `running`.
- Discovered the SSH host from provider metadata at `data[0].ip`.
- Verified TCP port 22 became reachable.
- Attempted exactly one bounded SSH authentication probe.
- Did not open an interactive shell, run remote commands, transfer files,
  forward ports, install packages, or train.
- Terminated the owned instance and verified final discovery was clean.
- SSH authentication failed with `host_key_verification_failed`.

The M056 failure was traced to the real SSH command omitting the reviewed
host-key and identity options. The offline fix now forces:

- `IdentitiesOnly=yes`
- an isolated `UserKnownHostsFile` under `/tmp`
- `StrictHostKeyChecking=accept-new`

The next live SSH milestone should be a single gated retry that proves the
fixed host-key handling in the real path. It must still be connectivity/auth
only.

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
- Remote commands are forbidden.
- `nvidia-smi`, remote `python`, and shell command collection are forbidden.
- `scp`, `sftp`, `rsync`, upload, and download are forbidden.
- Local, remote, dynamic, agent, and X11 forwarding are forbidden.
- Package installation, setup scripts, cloud-init, model download, data
  download, and training are forbidden.

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
- [docs/lambda_metadata_bootstrap_success.md](docs/lambda_metadata_bootstrap_success.md)
- [docs/lambda_metadata_bootstrap_closeout.md](docs/lambda_metadata_bootstrap_closeout.md)

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

Focused M056 SSH retry regression:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_lambda_m056_ssh_retry_execution.py \
  -o cache_dir=/tmp/decodilo-pytest-cache-m56-focused
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

The next safe remote-runtime milestone is a single supervised SSH
connectivity/authentication retry using the fixed M056 host-key policy. It
should:

- freshen read-only Lambda discovery,
- select a live available candidate,
- launch exactly one instance,
- discover host metadata,
- attempt one bounded SSH auth probe with isolated known-host handling,
- avoid shell/command/file-transfer/forwarding/install/training paths,
- terminate the owned instance,
- verify clean post-run discovery,
- record redacted diagnostics only.

Training remains out of scope.
