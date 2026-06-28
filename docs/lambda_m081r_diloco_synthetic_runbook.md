# Lambda M081R DiLoCo Synthetic Runbook Preview

M081R is a future-only supervised remote retry surface for the bounded
DiLoCo-shaped synthetic smoke command:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-smoke.json
```

This preview is non-executable. A live M081R run still requires fresh read-only
discovery, source/dependency bundle validation, manifest validation, plan/gate,
one-shot arming, operator confirmation, exactly one launch attempt, SSH banner
readiness before upload, local-wheelhouse-only dependency installation, bounded
artifact capture, owned-instance termination, and read-only termination
verification.

The command must remain synthetic and offline in behavior. It must not use
network access, package installation from the internet, data/model download,
real model training, torch, GPU dependencies, port forwarding, background
services, command chaining, arbitrary shell access, or arbitrary file reads.

The smoke currently reports `optimization_fidelity=diloco_shaped_protocol_only`;
it must not be described as full DiLoCo optimizer fidelity unless the active
path actually implements inner AdamW and outer Nesterov semantics.
