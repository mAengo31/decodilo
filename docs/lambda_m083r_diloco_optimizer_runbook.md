# Lambda M083R DiLoCo Optimizer Runbook Preview

M083R is a future-only supervised remote surface for the bounded optimizer
fidelity smoke command:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev diloco-optimizer-smoke \
  --synthetic \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-optimizer-smoke.json
```

This preview is non-executable. A live M083R run still requires fresh read-only
discovery, source/dependency bundle validation, manifest validation, plan/gate,
one-shot arming, operator confirmation, exactly one launch attempt, SSH banner
readiness before upload, local-wheelhouse-only dependency installation, bounded
artifact capture, owned-instance termination, and read-only termination
verification.

The command must remain synthetic and offline in behavior. It must not use
network access, package installation from the internet, data/model download,
real model training, torch, GPU dependencies, port forwarding, background
services, command chaining, arbitrary shell access, or arbitrary file reads.

The expected report validates tiny deterministic AdamW plus Nesterov optimizer
semantics only. It must not be described as full DiLoCo training or as model
parameter-fragment synchronization.
