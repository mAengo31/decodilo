# Lambda M085R Integrated DiLoCo Runbook Preview

M085R is a future supervised remote run of exactly one bounded integrated
synthetic DiLoCo command:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev integrated-diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-integrated-diloco-smoke.json
```

The command is local/offline inside the remote instance. Dependencies must come
only from the uploaded wheelhouse. It must not download data or models, install
from the internet, run real training, require torch/GPU, start background
processes, or claim full DiLoCo training.

The declared artifact path is `/tmp/decodilo-integrated-diloco-smoke.json`.
Artifact capture is allowed only for the manifest-declared path, with bounded
metadata, secret scan, parsed safe summary, and raw body persistence only when
the scan and JSON safety checks pass.

This file is a non-executable preview. A live M085R requires fresh source and
dependency validation, manifest validation, read-only discovery, plan/gate,
one-shot arming, reviewer bridge, verification, and explicit supervised
operator confirmation.
