# Lambda M087R Parameter-Fragment Runbook Preview

M087R is a future supervised remote run of exactly one bounded parameter-fragment
synthetic command:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev parameter-fragment-smoke \
  --synthetic \
  --fragments 2 \
  --max-steps 1 \
  --out /tmp/decodilo-parameter-fragment-smoke.json
```

The command is local/offline inside the remote instance. Dependencies must come
only from the uploaded wheelhouse. It must not download data or models, install
from the internet, run real training, require torch/GPU, start background
processes, or claim true model/layer fragmentation unless that path is genuinely
implemented.

The declared artifact path is `/tmp/decodilo-parameter-fragment-smoke.json`.
Artifact capture is allowed only for the manifest-declared path, with bounded
metadata, secret scan, parsed safe summary, and raw body persistence only when
the scan and JSON safety checks pass.

This file is a non-executable preview. A live M087R requires fresh source and
dependency validation, manifest validation, read-only discovery, plan/gate,
one-shot arming, reviewer bridge, verification, and explicit supervised
operator confirmation.
