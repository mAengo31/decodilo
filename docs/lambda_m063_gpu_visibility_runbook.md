# Lambda M063 GPU Visibility Runbook

M063 is the next proposed supervised milestone after M062. It may run only after
fresh operator approval and one-shot arming.

Future M063 shape:

- launch at most one approved Lambda instance,
- wait for host and SSH readiness,
- execute exactly
  `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader`,
- capture bounded redacted stdout/stderr,
- do not open an interactive shell,
- do not run Python, package installation, setup scripts, cloud-init, benchmarks,
  downloads, training, file transfer, or port forwarding,
- terminate the owned instance in the same supervised run,
- verify termination through Lambda read-only discovery/list/get.

The M062 runbook preview is non-executable and keeps `launch_ready=false` and
`launch_allowed=false`.
