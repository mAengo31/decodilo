# Lambda Runtime/Protocol Smoke Command

`python -m decodilo.cli dev runtime-smoke --synthetic --max-steps 1 --out <path>`
is a bounded local/offline Decodilo runtime/protocol smoke command.

It exercises more than argument parsing by running a tiny synthetic
`UpdateStream` global-update delivery/ack path and a deterministic
`EventLog`/`replay_event_log` protocol path. It does not train a model.

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

Current report fields include `runtime_smoke_status`, `synthetic`,
`max_steps`, `network_used`, `package_install_attempted`, `download_attempted`,
`training_attempted`, `torch_required`, `gpu_required`,
`background_process_started`, runtime check results, skipped checks with
reasons, bounded artifact size, and elapsed seconds.

The command is intended as the next bounded remote Decodilo runtime/protocol
smoke candidate after M073R2 tiny-smoke success. Remote use still requires a
separate supervised M075R milestone with fresh discovery, one-shot arming, and
operator confirmation.
