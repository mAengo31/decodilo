# Lambda Tiny Smoke Command

`python -m decodilo.cli dev tiny-smoke --synthetic --max-steps 1 --out <path>`
is a bounded local/offline Decodilo smoke command.

It is intended to be the first future remote Decodilo smoke after the M071R
remote runtime baseline. It exercises more than argument parsing by importing
core Decodilo protocol/runtime helper modules and validating a tiny in-memory
protocol plus metric path.

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

Current report fields include `smoke_status`, `synthetic`, `max_steps`,
`network_used`, `package_install_attempted`, `download_attempted`,
`training_attempted`, `torch_required`, `gpu_required`, runtime check results,
bounded artifact size, and elapsed seconds.

