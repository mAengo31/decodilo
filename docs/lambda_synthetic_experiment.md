# Lambda Synthetic Experiment Command

`python -m decodilo.cli dev synthetic-experiment --synthetic --max-steps 1 --out <path>`
is a bounded local/offline Decodilo synthetic experiment command.

It exercises a one-step synthetic runtime/protocol path beyond
`dev runtime-smoke`: a deterministic `UpdateStream` commit/update delivery path,
token-weighted synthetic learner delta merge, in-memory `EventLog`, and replay
validation. It is not real model training.

Safety contract:

- no network access
- no package installation
- no data, model, weight, package, or code downloads
- no real model training
- no torch requirement
- no GPU requirement
- no background process
- bounded JSON report written to `--out`
- `launch_ready=false`
- `launch_allowed=false`

The report includes `synthetic_experiment_status`, `synthetic`, `max_steps`,
unsafe-attempt flags, learner/runtime check status, update/commit check status,
replay/metric check status, artifact/report check status, useful synthetic step
counts, synthetic update counts, skipped checks with reasons, bounded artifact
size, and elapsed seconds.

This command is intended as the first bounded remote synthetic Decodilo
experiment candidate after the M075R4 runtime/protocol smoke baseline. Remote
use still requires a separate supervised M077R milestone with fresh gates and
operator confirmation.
