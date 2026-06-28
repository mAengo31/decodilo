# Lambda Learner/Syncer Smoke Command

`python -m decodilo.cli dev learner-syncer-smoke --synthetic --max-steps 1 --out <path>`
is a bounded local/offline Decodilo learner/syncer-shaped smoke command.

It exercises a deterministic one-step synthetic exchange beyond
`dev synthetic-experiment`: a synthetic learner update vector, token-weighted
syncer merge, `UpdateStream` commit/update acknowledgement, in-memory
`EventLog`, and replay validation. It does not construct real model training,
start syncer services, or open network sockets.

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

The report includes `learner_syncer_smoke_status`, synthetic arguments,
unsafe-attempt flags, learner/syncer/exchange/update/replay check status,
synthetic update counts, sync-round counts, global-version transition,
useful synthetic token count, stale and duplicate update counts, skipped checks
with reasons, bounded artifact size, and elapsed seconds.

This command is intended as the next bounded remote synthetic Decodilo
experiment candidate after the successful M077R first synthetic experiment
baseline. Remote use still requires a separate supervised M079R milestone with
fresh gates and operator confirmation.
