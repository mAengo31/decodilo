# Lambda GPU Visibility Command Policy

M062 defines a future-only M063 GPU visibility query. It does not execute the
query.

The only reviewed command is:

```bash
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
```

The policy rejects raw `nvidia-smi`, polling/looping, shell wrappers, command
chaining, `dmon`, topology/NVLink/reset commands, benchmarks, package
installation, file transfer, port forwarding, Python, and training.

M063 still requires a supervised launch, one-shot arming, exact command binding,
bounded output capture, owned termination, and termination verification.
